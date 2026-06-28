from .config import model
from .prompts import condense_prompt


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
