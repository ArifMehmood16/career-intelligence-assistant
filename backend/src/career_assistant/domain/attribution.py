"""Who produced a saved analysis, kept apart from the score arithmetic."""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AnalysisAttribution:
    provider: str
    model: str
    prompt_version: str
    rubric_version: str
    left_machine: bool
    failure_status: str | None = None
