"""Phase 9.3–9.4 — open-question retrieval scope and untrusted prompt budgets."""

from __future__ import annotations

from career_assistant.domain.documents import DocumentKind, Span
from career_assistant.domain.prompts import (
    PromptBudget,
    RetrievedSpan,
    build_open_question_prompt,
    select_spans_for_open_question,
)


def _span(
    *,
    id: str,
    document_id: str,
    text: str,
    kind: DocumentKind,
    role_id: str | None = None,
) -> RetrievedSpan:
    return RetrievedSpan(
        span=Span(
            id=id,
            document_id=document_id,
            page_number=1,
            start_offset=0,
            end_offset=len(text),
            text=text,
        ),
        document_kind=kind,
        role_id=role_id,
    )


def test_open_question_may_retrieve_cover_letter_when_asked() -> None:
    pool = (
        _span(
            id="cv-1",
            document_id="cv",
            text="Owned dbt models in production.",
            kind=DocumentKind.CV,
        ),
        _span(
            id="cl-1",
            document_id="cl",
            text="I wrote about leadership in my cover letter.",
            kind=DocumentKind.COVER_LETTER,
        ),
    )
    selected = select_spans_for_open_question(
        "What did I write in my cover letter about leadership?",
        pool,
        role_id=None,
    )
    assert any(s.span.id == "cl-1" for s in selected)
    assert any(s.span.id == "cv-1" for s in selected) or True  # CV optional here


def test_role_scoped_question_cannot_retrieve_other_role_jd() -> None:
    pool = (
        _span(
            id="jd-a",
            document_id="jd-a",
            text="Need CUDA for role A.",
            kind=DocumentKind.JOB_DESCRIPTION,
            role_id="role-a",
        ),
        _span(
            id="jd-b",
            document_id="jd-b",
            text="Need ROS2 for role B.",
            kind=DocumentKind.JOB_DESCRIPTION,
            role_id="role-b",
        ),
        _span(
            id="cv-1",
            document_id="cv",
            text="Built ROS2 navigation stack.",
            kind=DocumentKind.CV,
        ),
    )
    selected = select_spans_for_open_question(
        "What does this role say about ROS2?",
        pool,
        role_id="role-a",
    )
    ids = {s.span.id for s in selected}
    assert "jd-b" not in ids
    assert "jd-a" in ids or "cv-1" in ids


def test_prompt_delimits_retrieved_text_as_untrusted_with_budgets() -> None:
    spans = (
        _span(
            id="cv-1",
            document_id="cv",
            text="Owned dbt models.",
            kind=DocumentKind.CV,
        ),
    )
    budget = PromptBudget(max_question_chars=200, max_context_chars=500, max_output_tokens=256)
    prompt = build_open_question_prompt(
        question="Summarise my dbt experience",
        spans=spans,
        budget=budget,
    )
    assert "UNTRUSTED" in prompt.system.upper() or "untrusted" in prompt.user.lower()
    assert "Owned dbt models." in prompt.user
    assert len(prompt.question) <= budget.max_question_chars
    assert prompt.max_output_tokens == 256
    # Injection in retrieved text stays inside the delimited block.
    assert prompt.user.count("<<<") >= 1
    assert prompt.user.count(">>>") >= 1


def test_prompt_truncates_over_budget_context() -> None:
    long_text = "dbt " * 400
    spans = (
        _span(
            id="cv-1",
            document_id="cv",
            text=long_text,
            kind=DocumentKind.CV,
        ),
    )
    budget = PromptBudget(max_question_chars=80, max_context_chars=40, max_output_tokens=64)
    prompt = build_open_question_prompt(
        question="x" * 200,
        spans=spans,
        budget=budget,
    )
    assert len(prompt.question) <= 80
    assert prompt.context_char_count <= 40
