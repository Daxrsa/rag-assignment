from langchain_chroma import Chroma

from .config import RETRIEVAL_K, SIMILARITY_THRESHOLD, model
from .meta import is_meta_question
from .prompts import confirm_prompt, rag_prompt
from .retrieval import build_context, format_sources, rewrite_question


def rag_agent(
    question: str,
    history: list[tuple[str, str, str]],
    vector_store: Chroma,
) -> tuple[str, str]:
    """Returns (display_output, standalone_question_used_for_retrieval)."""

    # META path: user is asking us to confirm/repeat the previous answer.
    # Reuse the previous standalone question for retrieval; do NOT rewrite.
    if is_meta_question(question) and history:
        _prev_raw, prev_standalone, prev_answer = history[-1]
        print("[meta-question detected; re-verifying previous answer]")
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

        if answer.lower().startswith(("i don't know", "i do not know")):
            return "I don't know.", prev_standalone

        return answer + "\n" + format_sources(relevant), prev_standalone

    # NORMAL path: rewrite the question for retrieval, then answer with the grounded RAG prompt.
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

    if answer.lower().startswith(("i don't know", "i do not know")):
        return "I don't know.", standalone

    return answer + "\n" + format_sources(relevant), standalone
