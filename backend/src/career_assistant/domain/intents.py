"""Deterministic question intent routing — pure, no model, no I/O."""

from __future__ import annotations

import re
from enum import StrEnum


class Intent(StrEnum):
    GAPS = "gaps"
    FIT = "fit"
    COMPARE_ROLES = "compare_roles"
    EVIDENCE_FOR_REQUIREMENT = "evidence_for_requirement"
    INTERVIEW_PREPARATION = "interview_preparation"
    OPEN_QUESTION = "open_question"


_COMPARE = re.compile(
    r"\b(compare|comparison|across (these )?roles|stronger match|"
    r"which role|between (these )?roles)\b",
    re.IGNORECASE,
)
_EVIDENCE = re.compile(
    r"\b(evidence|citation|citations|show (me )?citations|"
    r"what (evidence|proof) (do i|have i)|for the .+ requirement|"
    r"for the .+ must[- ]have)\b",
    re.IGNORECASE,
)
_INTERVIEW = re.compile(
    r"\b(interview|prepare for|preparation|what will they (probe|ask)|"
    r"probe)\b",
    re.IGNORECASE,
)
_GAPS = re.compile(
    r"\b(gap|gaps|missing|am i missing|skills am i missing|"
    r"worth closing|close first|should i close)\b",
    re.IGNORECASE,
)
_FIT = re.compile(
    r"\b("
    r"how well do i\b|"
    r"fit score\b|"
    r"my fit\b|"
    r"do i fit\b|"
    r"fit (for|this) (role|job)\b|"
    r"match (for|this) role\b"
    r")",
    re.IGNORECASE,
)


def route_intent(question: str, *, role_id: str | None = None) -> Intent:
    """Classify a question into a structured or open intent.

    ``role_id`` is accepted for call-site convenience and does not change
    classification — scoping is applied later by the answering use case.
    """
    del role_id  # intentional: routing is text-only and deterministic
    text = question.strip()
    if not text:
        return Intent.OPEN_QUESTION

    # More specific structured intents win before broader fit/gap cues.
    if _COMPARE.search(text):
        return Intent.COMPARE_ROLES
    if _EVIDENCE.search(text):
        return Intent.EVIDENCE_FOR_REQUIREMENT
    if _INTERVIEW.search(text):
        return Intent.INTERVIEW_PREPARATION
    if _GAPS.search(text):
        return Intent.GAPS
    if _FIT.search(text):
        return Intent.FIT
    return Intent.OPEN_QUESTION
