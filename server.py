from rag.agent import rag_agent
from rag.config import MAX_HISTORY_TURNS
from rag.store import build_vector_store

PRESET_QUESTIONS = [
    "Why does Northpeak only offer 5 days PTO annually?",  # 1.
    "What is the revenue for Q2 2026?",  # 2.
    "Is there a remote work option?",  # 3.
    "What was the Q3 operating profit?",  # 4.
    "How does an employee request a fully remote work arrangement?",  # 5.
    "What does Northpeak Technologies do?",  # 6.
    "What are some open questions regarding the product?",  # 7.
    "What are some issues regarding the product?",  # 8.
    "Why has the service degraded over time?",  # 9.
    "Are you sure that it's due to staff allocation and not because of financial reasons?",  # 10.
    "Who is Elon Musk?",  # 11.
    "Give me a cake recipe.",  # 12.
    "I am confused about the invoice, i need clarification around it.",  # 13.
    "what happens if payments are missed?",  # 14.
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


if __name__ == "__main__":
    main()
