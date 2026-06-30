import argparse
import uuid
from collections import defaultdict

from evals.dataset import CASES
from rag.agent import rag_agent
from rag.config import MAX_HISTORY_TURNS
from rag.store import build_vector_store

PRESET_QUESTIONS = [case.question for case in CASES]


def print_menu() -> None:
    print("\nPreset questions:")
    for i, q in enumerate(PRESET_QUESTIONS, start=1):
        label = q if q else "(empty)"
        print(f"  {i:>2}. {label}")
    print("  m.     show this menu")
    print("  reset  clear conversation history")
    print("  q.     quit")


def main() -> None:
    vector_store = build_vector_store()

    print("RAG ready.")
    print_menu()
    print("\nType a number to ask a preset question, or type your own question.")

    chat_history: list[tuple[str, str, str]] = []

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("Bye")
            break
        if user_input.lower() == "m":
            print_menu()
            continue
        if user_input.lower() in {"reset", "clear"}:
            chat_history.clear()
            print("[conversation history cleared]")
            continue

        if user_input.isdigit():
            idx = int(user_input)
            if 1 <= idx <= len(PRESET_QUESTIONS):
                question = PRESET_QUESTIONS[idx - 1]
                if not question:
                    print(f"Preset {idx} is empty.")
                    continue
                print(f"You (preset {idx}): {question}")
            else:
                print(f"Pick a number between 1 and {len(PRESET_QUESTIONS)}.")
                continue
        else:
            question = user_input

        print("Assistant:")
        output, standalone, _top_score = rag_agent(question, chat_history, vector_store)
        print(output)

        # store only the answer portion (without the Sources block) in history
        answer_for_history = output.split("\nSources:", 1)[0].strip()
        chat_history.append((question, standalone, answer_for_history))
        if len(chat_history) > MAX_HISTORY_TURNS:
            chat_history = chat_history[-MAX_HISTORY_TURNS:]


def run_api(host: str, port: int) -> None:
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel
        import uvicorn
    except Exception as ex:
        raise RuntimeError(
            "API mode requires fastapi, pydantic, and uvicorn. "
            "Install them with: pip install fastapi uvicorn pydantic"
        ) from ex

    app = FastAPI(title="RAG Chat API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    vector_store = build_vector_store()
    sessions: dict[str, list[tuple[str, str, str]]] = defaultdict(list)

    class ChatRequest(BaseModel):
        message: str
        session_id: str | None = None
        company: str | None = None

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/chat")
    def chat(req: ChatRequest) -> dict[str, object]:
        message = req.message.strip()
        if not message:
            return {"error": "message is required"}

        session_id = req.session_id or str(uuid.uuid4())
        history = sessions[session_id]

        output, standalone, top_score = rag_agent(message, history, vector_store)

        answer_for_history = output.split("\nSources:", 1)[0].strip()
        history.append((message, standalone, answer_for_history))
        if len(history) > MAX_HISTORY_TURNS:
            sessions[session_id] = history[-MAX_HISTORY_TURNS:]

        return {
            "session_id": session_id,
            "answer": output,
            "top_score": top_score,
        }

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG local runner")
    parser.add_argument("--serve", action="store_true", help="Run as HTTP API server")
    parser.add_argument("--host", default="127.0.0.1", help="Host for API server")
    parser.add_argument("--port", type=int, default=8000, help="Port for API server")
    args = parser.parse_args()

    if args.serve:
        run_api(args.host, args.port)
    else:
        main()
