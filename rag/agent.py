from langchain_chroma import Chroma

from .config import (
    RETRIEVAL_K,
    SIMILARITY_THRESHOLD,
    SIMILARITY_THRESHOLD_TOP1,
    VERIFY_MIN_CHUNKS,
    VERIFY_QUESTION_LEN,
    model,
)
from .meta import is_meta_question
from .prompts import confirm_prompt, rag_prompt, verify_prompt
from .retrieval import build_context, format_sources, rewrite_question

import re

# Keywords whose presence in the question or answer signals a high-impact (policy /
# financial / legal / contractual) claim where a hallucination is costly.
_HIGH_IMPACT_KEYWORDS = re.compile(
    r"\b(policy|policies|fee|fees|penalty|penalties|terminat|warranty|liab|indemni|"
    r"sla|deadline|notice|salary|wage|bonus|pto|leave|invoice|refund|breach|"
    r"confidential|nda|contract|agreement|clause|shall|must|comply|tax|"
    r"revenue|profit|loss|cost|price|discount|expir)",
    re.IGNORECASE,
)
# Numbers, money, percentages, dates.
_NUMERIC_OR_DATE = re.compile(
    r"(\$\s?\d|\d+(?:\.\d+)?\s?%|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b|"
    r"\bq[1-4]\b|\bjan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r"|\b\d{2,}\b)",
    re.IGNORECASE,
)
_CITATION = re.compile(r"\[\d+\]")


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


def _is_high_impact(question: str, answer: str, relevant: list[tuple]) -> list[str]:
    """Return the list of high-impact triggers that fired (empty list = skip verifier).

    High-impact triggers (any one is enough to verify):
      - weak retrieval confidence (top score below floor)
      - sparse evidence (fewer than VERIFY_MIN_CHUNKS chunks survived)
      - long / multi-part question
      - answer contains numbers, dates, or money
      - question or answer mentions policy / legal / financial terms
      - answer has no citations (every grounded answer should cite)
    """
    top = max((s for _, s in relevant), default=0.0)
    reasons: list[str] = []
    if top < SIMILARITY_THRESHOLD:
        reasons.append(f"weak retrieval (top={top:.3f} < {SIMILARITY_THRESHOLD})")
    if len(relevant) < VERIFY_MIN_CHUNKS:
        reasons.append(f"sparse evidence (n={len(relevant)})")
    if len(question) > VERIFY_QUESTION_LEN or question.count("?") > 1 or " and " in question.lower():
        reasons.append("long/multi-part question")
    if _NUMERIC_OR_DATE.search(answer):
        reasons.append("numeric/date claim")
    if _HIGH_IMPACT_KEYWORDS.search(question) or _HIGH_IMPACT_KEYWORDS.search(answer):
        reasons.append("policy/legal/financial topic")
    if not _CITATION.search(answer):
        reasons.append("no citations in answer")
    return reasons


# Map verifier verdict to a 0-100 grounding score that we show the user.
_GROUNDING_SCORE = {"SUPPORTED": 100, "PARTIAL": 60, "UNSUPPORTED": 0}


def _verify_answer(question: str, answer: str, context: str) -> tuple[str, str, int]:
    """Run the grounding verifier. Returns (final_answer, verdict, grounding_score)."""
    prompt = verify_prompt.invoke({"question": question, "answer": answer, "context": context})
    raw = model.invoke(prompt).content.strip()

    verdict = "SUPPORTED"
    revised = ""
    for line in raw.splitlines():
        if line.upper().startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip().upper()
        elif line.upper().startswith("REVISED:"):
            revised = line.split(":", 1)[1].strip()
    if verdict not in _GROUNDING_SCORE:
        verdict = "SUPPORTED"

    score = _GROUNDING_SCORE[verdict]
    final = answer if (verdict == "SUPPORTED" or not revised) else revised
    return final, verdict, score


def _verification_line(triggers: list[str], verdict: str, score: int) -> str:
    return (
        f"[verification: TRIGGERED by {len(triggers)} signal(s) -> {', '.join(triggers)} "
        f"| verdict={verdict} | grounding={score}/100]"
    )


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

    triggers = _is_high_impact(standalone, answer, relevant)
    verification_line = ""
    if triggers:
        print(f"[high-impact answer; running verifier: {', '.join(triggers)}]")
        answer, verdict, score = _verify_answer(standalone, answer, context)
        verification_line = _verification_line(triggers, verdict, score) + "\n"
        if answer.lower().startswith(("i don't know", "i do not know")):
            return f"I don't know.\n{summary}\n{verification_line.rstrip()}", standalone, top

    return f"{summary}\n{verification_line}{answer}\n{format_sources(relevant)}", standalone, top

