import { useEffect, useMemo, useState } from 'react'

const CRM_API_BASE = import.meta.env.VITE_CRM_API_URL ?? 'http://localhost:5237'
const CHAT_API_BASE = import.meta.env.VITE_CHAT_API_URL ?? 'http://localhost:8000'
const TOKEN_STORAGE_KEY = 'crm_access_token'

function App() {
  const [mode, setMode] = useState('login')
  const [token, setToken] = useState(localStorage.getItem(TOKEN_STORAGE_KEY) ?? '')
  const [user, setUser] = useState(null)
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const [loginForm, setLoginForm] = useState({ email: '', password: '' })
  const [registerForm, setRegisterForm] = useState({
    email: '',
    password: '',
    displayName: '',
    company: '',
  })

  const [fileName, setFileName] = useState('')
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatMessages, setChatMessages] = useState([
    {
      role: 'assistant',
      content: 'Hi. Ask me anything about your company docs and I will help.',
    },
  ])

  const fileCount = useMemo(() => files.length, [files])

  useEffect(() => {
    if (!token) {
      setUser(null)
      setFiles([])
      return
    }

    void loadSession(token)
  }, [token])

  async function api(path, init = {}, accessToken = token) {
    const headers = {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    }

    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`
    }

    const response = await fetch(`${CRM_API_BASE}${path}`, {
      ...init,
      headers,
    })

    const text = await response.text()
    const payload = text ? tryParseJson(text) : null

    if (!response.ok) {
      const errorMessage = payload?.error ?? `Request failed: ${response.status}`
      throw new Error(errorMessage)
    }

    return payload
  }

  async function loadSession(accessToken) {
    setLoading(true)
    setMessage('')
    try {
      const currentUser = await api('/auth/getloggedinuser', {}, accessToken)
      setUser(currentUser)
      const companyFiles = await api('/files', {}, accessToken)
      setFiles(companyFiles ?? [])
    } catch (error) {
      clearSession()
      setMessage(error.message)
    } finally {
      setLoading(false)
    }
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    setToken('')
    setUser(null)
    setFiles([])
  }

  async function handleLogin(event) {
    event.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      const response = await api('/auth/login', {
        method: 'POST',
        body: JSON.stringify(loginForm),
      }, '')

      const accessToken = extractAccessToken(response)
      if (!accessToken) {
        throw new Error('Login succeeded but no access token was returned.')
      }

      localStorage.setItem(TOKEN_STORAGE_KEY, accessToken)
      setToken(accessToken)
      setLoginForm({ email: '', password: '' })
    } catch (error) {
      setMessage(error.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleRegister(event) {
    event.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      await api('/auth/register', {
        method: 'POST',
        body: JSON.stringify(registerForm),
      }, '')

      await handleAutoLogin(registerForm.email, registerForm.password)
      setRegisterForm({ email: '', password: '', displayName: '', company: '' })
    } catch (error) {
      setMessage(error.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleAutoLogin(email, password) {
    const response = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }, '')

    const accessToken = extractAccessToken(response)
    if (!accessToken) {
      throw new Error('Registration succeeded but auto-login failed to return a token.')
    }

    localStorage.setItem(TOKEN_STORAGE_KEY, accessToken)
    setToken(accessToken)
  }

  async function handleUpload(event) {
    event.preventDefault()
    if (!fileName.trim()) {
      setMessage('Please provide a file name or choose a file first.')
      return
    }

    setLoading(true)
    setMessage('')
    try {
      const created = await api('/files', {
        method: 'POST',
        body: JSON.stringify({ fileName: fileName.trim() }),
      })
      setFiles((prev) => [...prev, created])
      setFileName('')
    } catch (error) {
      setMessage(error.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteFile(fileId) {
    setLoading(true)
    setMessage('')
    try {
      await api(`/files/${fileId}`, { method: 'DELETE' })
      setFiles((prev) => prev.filter((file) => file.id !== fileId))
    } catch (error) {
      setMessage(error.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleChatSubmit(event) {
    event.preventDefault()
    const prompt = chatInput.trim()
    if (!prompt) {
      return
    }

    const nextMessages = [...chatMessages, { role: 'user', content: prompt }]
    setChatMessages(nextMessages)
    setChatInput('')
    setChatLoading(true)

    try {
      const response = await fetch(`${CHAT_API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt, company: user?.company ?? null }),
      })

      const text = await response.text()
      const payload = text ? tryParseJson(text) : null

      if (!response.ok) {
        throw new Error(payload?.error ?? `Chat request failed: ${response.status}`)
      }

      const answer = payload?.answer ?? payload?.response ?? 'No answer returned by chat service.'
      setChatMessages((prev) => [...prev, { role: 'assistant', content: answer }])
    } catch (error) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            `I could not reach the AI service (${CHAT_API_BASE}/chat). ` +
            `Set VITE_CHAT_API_URL if needed. Details: ${error.message}`,
        },
      ])
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="top-nav">
        {user ? (
          <div className="user-box">
            <div>
              <p className="muted">Signed in as</p>
              <p className="user-name">{user.displayName}</p>
            </div>
            <button type="button" onClick={clearSession}>Log out</button>
          </div>
        ) : (
          <div className="auth-switch">
            <button
              type="button"
              className={mode === 'login' ? 'active' : ''}
              onClick={() => setMode('login')}
            >
              Login
            </button>
            <button
              type="button"
              className={mode === 'register' ? 'active' : ''}
              onClick={() => setMode('register')}
            >
              Register
            </button>
          </div>
        )}
      </header>

      {message && <p className="flash">{message}</p>}

      {!user ? (
        <section className="auth-card">
          {mode === 'login' ? (
            <form onSubmit={handleLogin}>
              <h2>Login</h2>
              <label>
                Email
                <input
                  type="email"
                  value={loginForm.email}
                  onChange={(event) => setLoginForm((prev) => ({ ...prev, email: event.target.value }))}
                  required
                />
              </label>
              <label>
                Password
                <input
                  type="password"
                  value={loginForm.password}
                  onChange={(event) => setLoginForm((prev) => ({ ...prev, password: event.target.value }))}
                  required
                />
              </label>
              <button type="submit" disabled={loading}>{loading ? 'Signing in...' : 'Sign in'}</button>
            </form>
          ) : (
            <form onSubmit={handleRegister}>
              <h2>Register</h2>
              <label>
                Display name
                <input
                  value={registerForm.displayName}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, displayName: event.target.value }))}
                  placeholder="Alex Rivera"
                />
              </label>
              <label>
                Company
                <input
                  value={registerForm.company}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, company: event.target.value }))}
                  required
                  placeholder="Riverstone"
                />
              </label>
              <label>
                Email
                <input
                  type="email"
                  value={registerForm.email}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, email: event.target.value }))}
                  required
                />
              </label>
              <label>
                Password
                <input
                  type="password"
                  value={registerForm.password}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, password: event.target.value }))}
                  required
                />
              </label>
              <button type="submit" disabled={loading}>{loading ? 'Creating account...' : 'Create account'}</button>
            </form>
          )}
        </section>
      ) : (
        <main className="dashboard-grid">
          <section className="panel">
            <h2>{user.company} Dashboard</h2>
            <p className="muted">Your company space and file inventory.</p>
            <div className="metrics">
              <article>
                <p>Total files</p>
                <strong>{fileCount}</strong>
              </article>
              <article>
                <p>Last update</p>
                <strong>{files.at(-1)?.createdAtUtc ? new Date(files.at(-1).createdAtUtc).toLocaleString() : 'No files yet'}</strong>
              </article>
            </div>
          </section>

          <section className="panel">
            <h2>Upload files</h2>
            <form onSubmit={handleUpload} className="upload-form">
              <label>
                Choose file
                <input
                  type="file"
                  onChange={(event) => {
                    const chosenFile = event.target.files?.[0]
                    if (chosenFile) {
                      setFileName(chosenFile.name)
                    }
                  }}
                />
              </label>
              <label>
                File name sent to API
                <input
                  value={fileName}
                  onChange={(event) => setFileName(event.target.value)}
                  placeholder="quarterly-report.pdf"
                  required
                />
              </label>
              <button type="submit" disabled={loading}>{loading ? 'Uploading...' : 'Upload'}</button>
            </form>

            <ul className="file-list">
              {files.map((file) => (
                <li key={file.id}>
                  <div>
                    <p className="file-name">{file.fileName}</p>
                    <p className="muted">{new Date(file.createdAtUtc).toLocaleString()}</p>
                  </div>
                  <button type="button" onClick={() => handleDeleteFile(file.id)}>Delete</button>
                </li>
              ))}
              {files.length === 0 && <li className="empty-row">No files uploaded yet.</li>}
            </ul>
          </section>

          <section className="panel chat-panel">
            <h2>Ask the AI Agent</h2>
            <p className="muted">Connected to {CHAT_API_BASE}/chat</p>

            <div className="chat-stream">
              {chatMessages.map((entry, index) => (
                <article key={`${entry.role}-${index}`} className={`bubble ${entry.role}`}>
                  <p>{entry.content}</p>
                </article>
              ))}
            </div>

            <form onSubmit={handleChatSubmit} className="chat-form">
              <input
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                placeholder="Ask about policies, contracts, or reports..."
                required
              />
              <button type="submit" disabled={chatLoading}>{chatLoading ? 'Thinking...' : 'Send'}</button>
            </form>
          </section>
        </main>
      )}
    </div>
  )
}

function extractAccessToken(payload) {
  return (
    payload?.accessToken ??
    payload?.access_token ??
    payload?.token ??
    payload?.bearerToken ??
    ''
  )
}

function tryParseJson(value) {
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

export default App
