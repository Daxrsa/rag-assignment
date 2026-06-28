"""Run the RAG agent against evals/dataset.py and print a pass/fail report.

Usage:
    python -m evals.run_eval                 # run everything
    python -m evals.run_eval --ids pto_false_premise q2_total_revenue
    python -m evals.run_eval --category factual
    python -m evals.run_eval --verbose       # print the answer body for every case

Exit code is 0 if every case passed, 1 otherwise — suitable for CI gating.
"""

import argparse
import os
import re
import sys
import time

from evals.dataset import CASES, EvalCase
from rag.agent import rag_agent
from rag.store import build_vector_store

SOURCE_LINE = re.compile(r"^\s*\[\d+\]\s+(\S+)", re.MULTILINE)


def parse_citations(output: str) -> list[str]:
    if "\nSources:" not in output:
        return []
    block = output.split("\nSources:", 1)[1]
    return [os.path.basename(m) for m in SOURCE_LINE.findall(block)]


def is_refusal(output: str) -> bool:
    body = output.split("\nSources:", 1)[0]
    lines = [ln for ln in body.splitlines() if not ln.lstrip().startswith("[retrieval similarity")]
    text = "\n".join(lines).strip().lower()
    return text.startswith(("i don't know", "i do not know"))


def grade(case: EvalCase, output: str) -> dict:
    citations = parse_citations(output)
    refused = is_refusal(output)
    body = output.split("\nSources:", 1)[0].lower()
    checks: dict[str, bool | None] = {}

    if case.expected_behavior == "refuse":
        checks["refusal_ok"] = refused
        return {"checks": checks, "citations": citations, "refused": refused}

    checks["refusal_ok"] = not refused
    checks["answer_match"] = (
        all(s.lower() in body for s in case.expected_answer_contains)
        if case.expected_answer_contains
        else None
    )
    checks["citation_ok"] = (
        bool(set(citations) & set(case.expected_sources)) if case.expected_sources else None
    )
    return {"checks": checks, "citations": citations, "refused": refused}


def fmt_check(value: bool | None) -> str:
    if value is None:
        return " -  "
    return "PASS" if value else "FAIL"


def case_passed(checks: dict) -> bool:
    return all(v for v in checks.values() if v is not None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the RAG agent against the eval set.")
    parser.add_argument("--ids", nargs="*", help="Only run cases with these ids.")
    parser.add_argument("--category", help="Only run cases in this category.")
    parser.add_argument("--verbose", action="store_true", help="Print full answer for every case.")
    args = parser.parse_args(argv)

    cases = list(CASES)
    if args.ids:
        wanted = set(args.ids)
        cases = [c for c in cases if c.id in wanted]
    if args.category:
        cases = [c for c in cases if c.category == args.category]
    if not cases:
        print("No cases matched the filters.", file=sys.stderr)
        return 2

    print("Building vector store...")
    vector_store = build_vector_store()
    print(f"Running {len(cases)} case(s).\n")

    results: list[tuple[EvalCase, dict, float, float, str]] = []
    for case in cases:
        history = [tuple(h) for h in case.history]
        t0 = time.perf_counter()
        output, _standalone, top_score = rag_agent(case.question, history, vector_store)
        latency = time.perf_counter() - t0
        graded = grade(case, output)
        results.append((case, graded, top_score, latency, output))

        checks_str = "  ".join(f"{k}={fmt_check(v)}" for k, v in graded["checks"].items())
        flag = " OK " if case_passed(graded["checks"]) else "FAIL"
        print(f"[{flag}] {case.id:35s} top={top_score:.3f}  {latency:5.2f}s  {checks_str}")

        if args.verbose or not case_passed(graded["checks"]):
            answer_body = output.split("\nSources:", 1)[0].strip()
            print(f"        Q: {case.question}")
            print(f"        cites: {graded['citations']}")
            print(f"        expect cites: {list(case.expected_sources)}")
            print(f"        answer: {answer_body[:400]}")
            print()

    total = len(results)
    passed = sum(1 for _, g, *_ in results if case_passed(g["checks"]))
    print()
    print(f"Aggregate: {passed}/{total} passed ({passed / total * 100:.0f}%)")

    by_cat: dict[str, list[bool]] = {}
    for case, g, *_ in results:
        by_cat.setdefault(case.category, []).append(case_passed(g["checks"]))
    print("By category:")
    for cat, oks in sorted(by_cat.items()):
        print(f"  {cat:18s} {sum(oks)}/{len(oks)}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
