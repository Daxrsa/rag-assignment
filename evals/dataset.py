"""Structured evaluation set for the Northpeak RAG service.

Each case is one demo question plus the metadata a harness needs to grade it:
which file(s) should be cited, which substrings must appear in the answer,
whether the agent should refuse, and (for multi-turn cases) the prior history
to replay first. The history tuple shape matches what `rag_agent` expects:
(raw_question, standalone, answer).
"""

from dataclasses import dataclass
from typing import Literal

Behavior = Literal[
    "answer",
    "refuse",
    "correct_false_premise",
    "meta_confirm",
]

Category = Literal[
    "factual",
    "false_premise",
    "out_of_scope",
    "meta",
    "ambiguous",
]


@dataclass(frozen=True)
class EvalCase:
    id: str
    question: str
    category: Category
    expected_behavior: Behavior
    expected_answer_contains: tuple[str, ...] = ()
    expected_sources: tuple[str, ...] = ()
    history: tuple[tuple[str, str, str], ...] = ()
    notes: str = ""


CASES: tuple[EvalCase, ...] = (
    EvalCase(
        id="pto_false_premise",
        question="Why does Northpeak only offer 5 days PTO annually?",
        category="false_premise",
        expected_behavior="correct_false_premise",
        expected_answer_contains=("21",),
        expected_sources=("01_employee_handbook.md",),
        notes="False premise. Correct value: 21 days/year (1.75/month).",
    ),
    EvalCase(
        id="q2_total_revenue",
        question="What is the revenue for Q2 2026?",
        category="factual",
        expected_behavior="answer",
        expected_answer_contains=("649,500",),
        expected_sources=("02_q2_financial_summary.md",),
    ),
    EvalCase(
        id="remote_work_option",
        question="Is there a remote work option?",
        category="factual",
        expected_behavior="answer",
        expected_answer_contains=("two days per week",),
        expected_sources=("01_employee_handbook.md",),
        notes="Hybrid: min 2 days in office; fully remote needs VP approval.",
    ),
    EvalCase(
        id="q3_profit_unknown",
        question="What was the Q3 operating profit?",
        category="out_of_scope",
        expected_behavior="refuse",
        notes="Only Q2 2026 financials exist; agent must refuse.",
    ),
    EvalCase(
        id="request_fully_remote",
        question="How does an employee request a fully remote work arrangement?",
        category="factual",
        expected_behavior="answer",
        expected_answer_contains=("VP-level approval",),
        expected_sources=("01_employee_handbook.md",),
    ),
    EvalCase(
        id="northpeak_description",
        question="What does Northpeak Technologies do?",
        category="ambiguous",
        expected_behavior="refuse",
        notes=(
            "No document explicitly states what Northpeak does as a company. "
            "Under the no-inference rule the agent should refuse; flag as a "
            "known ambiguity in the report."
        ),
    ),
    EvalCase(
        id="product_open_questions",
        question="What are some open questions regarding the product?",
        category="factual",
        expected_behavior="answer",
        expected_answer_contains=("legacy onboarding",),
        expected_sources=("04_product_sync_notes.md",),
    ),
    EvalCase(
        id="product_issues",
        question="What are some issues regarding the product?",
        category="factual",
        expected_behavior="answer",
        expected_answer_contains=("analytics",),
        expected_sources=("04_product_sync_notes.md", "05_crm_riverstone.md"),
        notes=(
            "Issues span product sync (onboarding too many steps, bulk-import "
            "blocked on permissions) and the CRM record (Riverstone analytics "
            "dashboard slowness)."
        ),
    ),
    EvalCase(
        id="service_degraded_cause",
        question="Why has the service degraded over time?",
        category="factual",
        expected_behavior="answer",
        expected_answer_contains=("analytics",),
        expected_sources=("02_q2_financial_summary.md", "05_crm_riverstone.md"),
        notes="Links CRM slowness to the May analytics workload migration.",
    ),
    EvalCase(
        id="service_degraded_meta_confirm",
        question="Are you sure that it's due to staff allocation and not because of financial reasons?",
        category="meta",
        expected_behavior="meta_confirm",
        expected_answer_contains=("staff",),
        expected_sources=("02_q2_financial_summary.md",),
        history=(
            (
                "Why has the service degraded over time?",
                "Why has the service degraded over time?",
                (
                    "The professional services revenue decline is attributed "
                    "to two delivery staff being reallocated to the internal "
                    "platform project in May 2026."
                ),
            ),
        ),
        notes="Must trigger is_meta_question and reuse the previous standalone.",
    ),
    EvalCase(
        id="elon_musk_oos",
        question="Who is Elon Musk?",
        category="out_of_scope",
        expected_behavior="refuse",
    ),
    EvalCase(
        id="cake_recipe_oos",
        question="Give me a cake recipe.",
        category="out_of_scope",
        expected_behavior="refuse",
    ),
    EvalCase(
        id="invoice_clarification",
        question="I am confused about the invoice, i need clarification around it.",
        category="ambiguous",
        expected_behavior="answer",
        expected_answer_contains=("INV-2026-1042",),
        expected_sources=("06_invoice_1042.md",),
        notes=(
            "Vague request; only one invoice exists, so the agent should "
            "summarise INV-2026-1042. A clarify-first behavior would also be "
            "acceptable if added later."
        ),
    ),
    EvalCase(
        id="late_payment_terms",
        question="what happens if payments are missed?",
        category="factual",
        expected_behavior="answer",
        expected_answer_contains=("1.5%",),
        expected_sources=("03_acme_services_agreement.md", "06_invoice_1042.md"),
    ),
)
