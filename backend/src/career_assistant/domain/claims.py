"""Claim — a CV evidence unit with justifying source spans."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Claim:
    id: str
    competency: str
    context: str
    duration_signal: str
    recency_signal: str
    source_span_ids: tuple[str, ...]
    extraction_confidence: float

    def __post_init__(self) -> None:
        if not self.context.strip():
            raise ValueError("claim context must be non-empty")
        if not self.source_span_ids:
            raise ValueError("claim must cite at least one source span")
        if not 0.0 <= self.extraction_confidence <= 1.0:
            raise ValueError("extraction_confidence must be between 0 and 1")
        if self.recency_signal not in {"recent", "mid", "old", "undated"}:
            raise ValueError(f"unknown recency_signal: {self.recency_signal!r}")
