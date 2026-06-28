from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import re

load_dotenv()

# In-memory, non-persistent
# Multi-turn: history-aware retrieval via query rewriting
# No reranker, no hybrid search, no tool-calling planner, no multi-step agent loop

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

# production vector store: Chroma with on-disk persistence and cosine space.
# relevance scores from this collection are normalized to [0, 1] (higher = better),
# so SIMILARITY_THRESHOLD below keeps its meaning.
DATA_DIR = "/Users/daorsa/Documents/Software/rag-assignment/sample_documents"
CHROMA_DIR = "/Users/daorsa/Documents/Software/rag-assignment/.chroma"
COLLECTION_NAME = "rag_assignment"
FILE_PATTERNS = ["**/*.txt", "**/*.md"]

vector_store = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings_model,
    persist_directory=CHROMA_DIR,
    collection_metadata={"hnsw:space": "cosine"},
)

# only (re)index when the persistent collection is empty
if vector_store._collection.count() == 0:
    loaders = [
        DirectoryLoader(DATA_DIR, glob=pattern, loader_cls=TextLoader, silent_errors=True)
        for pattern in FILE_PATTERNS
    ]

    docs = []
    for loader in loaders:
        docs.extend(loader.load())

    if not docs:
        raise ValueError(f"No documents found in {DATA_DIR} for patterns: {FILE_PATTERNS}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=200,
        add_start_index=True,
    )
    split_docs = splitter.split_documents(docs)
    vector_store.add_documents(split_docs)

# retrieval settings
# - RETRIEVAL_K: how many candidate chunks to pull
# - SIMILARITY_THRESHOLD: cosine similarity floor; chunks below this are discarded.
#   Raise this if you still see hallucinations, lower it if it refuses too often.
# - MAX_HISTORY_TURNS: how many prior (question, answer) pairs to keep for query rewriting
RETRIEVAL_K = 6
SIMILARITY_THRESHOLD = 0.30
MAX_HISTORY_TURNS = 5

# prompt used to rewrite a follow-up question into a standalone one, using prior turns.
# this is what gets EMBEDDED for retrieval - the user's raw question may be too vague.
condense_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You rewrite the user's latest question into a STANDALONE question, using the chat history to resolve any references "
            "(pronouns like 'it', 'they', 'that', elided subjects, follow-ups like 'and for new hires?'). "
            "Output ONLY the rewritten standalone question. Do not answer it. Do not add explanation, quotes, or prefixes. "
            "If the question is already standalone, output it unchanged.",
        ),
        (
            "human",
            "Chat history:\n{history}\n\nLatest question:\n{question}\n\nStandalone question:",
        ),
    ]
)

# prompt used when the user asks a META question ("are you sure?", "really?", etc.).
# we re-verify the PREVIOUS answer against freshly retrieved context, instead of
# treating the meta question as a new claim to scan.
confirm_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are verifying whether a previously given answer is still supported by the provided context. "
            "Use ONLY the context. Do not use prior knowledge.\n"
            "- If the context still supports the previous answer, reply: 'Yes. <briefly restate the supported claim with citations like [n]>'\n"
            "- If the context explicitly states a mutually exclusive value for that same fact, reply in the form: 'No. According to the context, <correct value from context> [n].'\n"
            "- If the context does not address the previous claim at all, reply with EXACTLY: I don't know.",
        ),
        (
            "human",
            "Previous question:\n{prev_question}\n\nPrevious answer:\n{prev_answer}\n\nContext:\n{context}",
        ),
    ]
)

# meta-question detection. these short, history-dependent inputs ask the assistant
# to confirm or repeat its previous statement; they must NOT be rewritten into a
# claim-verification question.
META_QUESTION_PATTERNS = [
    r"^(are |you )?(really |absolutely |totally |actually )?sure\??$",
    r"^are you (really |absolutely |totally |actually )?sure(\?| .*)?$",
    r"^really\??$",
    r"^seriously\??$",
    r"^honestly\??$",
    r"^is that (right|true|correct|so)\??$",
    r"^that('?s| is) (right|true|correct)\??$",
    r"^can you confirm(\?| .*)?$",
    r"^please confirm(\?| .*)?$",
    r"^(say|repeat) that again\??$",
    r"^are you certain(\?| .*)?$",
    r"^(but )?are you (really |absolutely |totally )?sure(\?| .*)?$",
]

def is_meta_question(text: str) -> bool:
    t = text.strip().lower()
    return any(re.match(p, t) for p in META_QUESTION_PATTERNS)

# define a prompt template for the RAG agent
rag_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a grounded RAG assistant. You can converse naturally about the documents in the context "
            "(summarize, list, compare, explain, give overviews), but every factual claim you make must be "
            "traceable to the provided context. Follow these rules without exception:\n"
            "1. GROUNDING. Use ONLY facts present in the provided context. Do not use prior knowledge. "
            "Do not infer, estimate, extrapolate, or invent details that are not stated. You may paraphrase "
            "and reorganize, but you may not add facts.\n"
            "2. SCOPE. Answer the kind of thing the user asked for:\n"
            "   - Specific factoid ('when', 'who', 'how much'): give the specific fact.\n"
            "   - Open-ended ('tell me about X', 'summarize Y', 'what does the contract say about Z'): "
            "give a concise grounded summary drawn ONLY from the relevant context, organized as short "
            "bullet points or 2-4 sentences. Stick to what's in the context; do not pad.\n"
            "   - Yes/no: answer yes or no, then briefly justify from the context.\n"
            "3. CORRECTION. If the user's question asserts a factual claim that the context explicitly "
            "contradicts with a mutually exclusive value, correct them: \"No. According to the context, "
            "<correct value> [n].\" Then stop; the original question is moot. Differences in phrasing or "
            "precision that are still logically compatible are NOT contradictions.\n"
            "4. INSUFFICIENT CONTEXT. If the context contains nothing relevant to the user's question, "
            "reply with EXACTLY: I don't know.\n"
            "   If the context is partially relevant (some aspects covered, others not), answer what IS "
            "supported and then add one short sentence noting which specific aspect the context does not "
            "cover. Do not guess the missing part.\n"
            "5. CITATIONS. Cite the source numbers like [1], [2] for every factual claim. Group citations "
            "at the end of the sentence or bullet they support.\n"
            "6. STYLE. Be conversational and concise. Do not apologize, do not narrate what the context "
            "contains in the abstract, do not offer speculation hedged as 'might' or 'probably'.",
        ),
        (
            "human",
            "Question:\n{question}\n\nContext:\n{context}",
        ),
    ]
)

def format_history(history: list[tuple[str, str, str]]) -> str:
    if not history:
        return "(no prior turns)"
    return "\n".join(f"User: {q}\nAssistant: {a}" for q, _, a in history)

def rewrite_question(question: str, history: list[tuple[str, str, str]]) -> str:
    if not history:
        return question
    prompt = condense_prompt.invoke({"history": format_history(history), "question": question})
    rewritten = model.invoke(prompt).content.strip().strip('"').strip("'").strip()
    return rewritten or question

def build_context(relevant) -> str:
    parts = []
    for i, (doc, score) in enumerate(relevant, start=1):
        source = doc.metadata.get("source", "unknown")
        start = doc.metadata.get("start_index", "?")
        parts.append(
            f"[{i}] Source: {source} (start_index={start}, score={score:.3f})\n{doc.page_content}"
        )
    return "\n\n".join(parts)

def format_sources(relevant) -> str:
    lines = ["", "Sources:"]
    for i, (doc, score) in enumerate(relevant, start=1):
        source = doc.metadata.get("source", "unknown")
        start = doc.metadata.get("start_index", "?")
        end = start + len(doc.page_content) if isinstance(start, int) else "?"
        excerpt = doc.page_content.strip().replace("\n", " ")
        if len(excerpt) > 300:
            excerpt = excerpt[:300] + "..."
        lines.append(
            f"  [{i}] {source}  (chars {start}-{end}, score={score:.3f})\n      \"{excerpt}\""
        )
    return "\n".join(lines)

def rag_agent(question: str, history: list[tuple[str, str, str]]) -> tuple[str, str]:
    """Returns (display_output, standalone_question_used_for_retrieval)."""

    # META path: user is asking us to confirm/repeat the previous answer.
    # Reuse the previous standalone question for retrieval; do NOT rewrite.
    if is_meta_question(question) and history:
        prev_question_raw, prev_standalone, prev_answer = history[-1]
        print(f"[meta-question detected; re-verifying previous answer]")
        print(f"[retrieval query: {prev_standalone}]")

        scored = vector_store.similarity_search_with_relevance_scores(prev_standalone, k=RETRIEVAL_K)
        relevant = [(doc, score) for doc, score in scored if score >= SIMILARITY_THRESHOLD]

        if not relevant:
            return "I don't know.", prev_standalone

        context = build_context(relevant)
        prompt = confirm_prompt.invoke({
            "prev_question": prev_standalone,
            "prev_answer": prev_answer,
            "context": context,
        })
        answer = model.invoke(prompt).content.strip()

        if answer.lower().startswith("i don't know") or answer.lower().startswith("i do not know"):
            return "I don't know.", prev_standalone

        return answer + "\n" + format_sources(relevant), prev_standalone

    # NORMAL path: rewrite the question for retrieval, then answer with strict RAG prompt.
    standalone = rewrite_question(question, history)
    if standalone != question:
        print(f"[retrieval query: {standalone}]")

    scored = vector_store.similarity_search_with_relevance_scores(standalone, k=RETRIEVAL_K)
    relevant = [(doc, score) for doc, score in scored if score >= SIMILARITY_THRESHOLD]

    if not relevant:
        return "I don't know.", standalone

    context = build_context(relevant)
    prompt = rag_prompt.invoke({"question": standalone, "context": context})
    answer = model.invoke(prompt).content.strip()

    if answer.lower().startswith("i don't know") or answer.lower().startswith("i do not know"):
        return "I don't know.", standalone

    return answer + "\n" + format_sources(relevant), standalone

# Preset questions the user can pick by number at the prompt.
# Add or edit entries here; the menu will update automatically.
PRESET_QUESTIONS = [
    "Why does Northpeak only offer 5 days PTO annually?",  # 1.
    "What is the revenue for Q2 2026?",  # 2.
    "Is there a remote work option?",  # 3.
    "What was the Q3 operating profit?",  # 4.
    "How does an employee request a fully remote work arrangement?",  # 5.
    "What does Northpeak Technologies do?",  # 6.
    "",  # 7.
    "",  # 8.
    "",  # 9.
    "",  # 10.
    "",  # 11.
    "",  # 12.
    "",  # 13.
    "",  # 14.
    "",  # 15.
]

def print_menu() -> None:
    print("\nPreset questions:")
    for i, q in enumerate(PRESET_QUESTIONS, start=1):
        label = q if q else "(empty)"
        print(f"  {i:>2}. {label}")
    print("  m.     show this menu")
    print("  reset  clear conversation history")
    print("  q.     quit")

if __name__ == "__main__":
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
        output, standalone = rag_agent(question, chat_history)
        print(output)

        # store only the answer portion (without the Sources block) in history
        answer_for_history = output.split("\nSources:", 1)[0].strip()
        chat_history.append((question, standalone, answer_for_history))
        if len(chat_history) > MAX_HISTORY_TURNS:
            chat_history = chat_history[-MAX_HISTORY_TURNS:]