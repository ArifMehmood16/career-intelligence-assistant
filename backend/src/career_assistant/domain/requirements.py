"""Requirement — a job-description claim unit with a justifying source span."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Requirement:
    id: str
    text: str
    competency: str
    seniority_signal: str | None
    must_have: bool
    source_span_id: str
    extraction_confidence: float
    is_vague: bool

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("requirement text must be non-empty")
        if not 0.0 <= self.extraction_confidence <= 1.0:
            raise ValueError("extraction_confidence must be between 0 and 1")
