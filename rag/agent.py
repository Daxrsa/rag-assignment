from langchain_chroma import Chroma

from .config import RETRIEVAL_K, SIMILARITY_THRESHOLD, SIMILARITY_THRESHOLD_TOP1, model
from .meta import is_meta_question
from .prompts import confirm_prompt, rag_prompt
from .retrieval import build_context, format_sources, rewrite_question


def _filter_by_threshold(scored: list[tuple]) -> list[tuple]:
    """Keep chunks above SIMILARITY_THRESHOLD, plus the top-1 if it clears the softer floor.

    Lets borderline-but-clearly-best matches through (e.g. colloquial paraphrases of
    corpus wording) without admitting unrelated chunks at ranks 2+.
    """
    if not scored:
        return []
    relevant = [(doc, score) for doc, score in scored if score >= SIMILARITY_THRESHOLD]
    if not relevant and scored[0][1] >= SIMILARITY_THRESHOLD_TOP1:
        relevant = [scored[0]]
    return relevant


def _score_summary(relevant: list[tuple]) -> tuple[float, str]:
    scores = [s for _, s in relevant]
    top = max(scores)
    mean = sum(scores) / len(scores)
    return top, f"[retrieval similarity: top={top:.3f}, mean={mean:.3f}, n={len(scores)}]"


def rag_agent(
    question: str,
    history: list[tuple[str, str, str]],
    vector_store: Chroma,
) -> tuple[str, str, float]:
    """Returns (display_output, standalone_question_used_for_retrieval, top_similarity_score).

    top_similarity_score is the highest cosine-similarity score among the chunks that
    passed SIMILARITY_THRESHOLD, or 0.0 if nothing made the cut.
    """

    # META path: user is asking us to confirm/repeat the previous answer.
    # Reuse the previous standalone question for retrieval; do NOT rewrite.
    if is_meta_question(question) and history:
        _prev_raw, prev_standalone, prev_answer = history[-1]
        print("[meta-question detected; re-verifying previous answer]")
        print(f"[retrieval query: {prev_standalone}]")

        scored = vector_store.similarity_search_with_relevance_scores(prev_standalone, k=RETRIEVAL_K)
        relevant = _filter_by_threshold(scored)

        if not relevant:
            return "I don't know.\n[retrieval similarity: no chunks above threshold]", prev_standalone, 0.0

        context = build_context(relevant)
        prompt = confirm_prompt.invoke({
            "prev_question": prev_standalone,
            "prev_answer": prev_answer,
            "context": context,
        })
        answer = model.invoke(prompt).content.strip()
        top, summary = _score_summary(relevant)

        if answer.lower().startswith(("i don't know", "i do not know")):
            return f"I don't know.\n{summary}", prev_standalone, top

        return f"{summary}\n{answer}\n{format_sources(relevant)}", prev_standalone, top

    # NORMAL path: rewrite the question for retrieval, then answer with the grounded RAG prompt.
    standalone = rewrite_question(question, history)
    if standalone != question:
        print(f"[retrieval query: {standalone}]")

    scored = vector_store.similarity_search_with_relevance_scores(standalone, k=RETRIEVAL_K)
    relevant = _filter_by_threshold(scored)

    if not relevant:
        return "I don't know.\n[retrieval similarity: no chunks above threshold]", standalone, 0.0

    context = build_context(relevant)
    prompt = rag_prompt.invoke({"question": standalone, "context": context})
    answer = model.invoke(prompt).content.strip()
    top, summary = _score_summary(relevant)

    if answer.lower().startswith(("i don't know", "i do not know")):
        return f"I don't know.\n{summary}", standalone, top

    return f"{summary}\n{answer}\n{format_sources(relevant)}", standalone, top

