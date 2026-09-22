"""Who produced a saved analysis, kept apart from the score arithmetic."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from career_assistant.domain.mapping import MappingReason, RequirementMapping

RUBRIC_VERSION = "scoring-rubric-v1"


@dataclass(frozen=True, slots=True)
class AnalysisAttribution:
    provider: str
    model: str
    prompt_version: str
    rubric_version: str
    left_machine: bool
    failure_status: str | None = None


def analysis_failure_status(
    mappings: Sequence[RequirementMapping],
) -> str | None:
    """A missing assessment is a failed analysis, not a low fit score."""
    incomplete = MappingReason.ASSESSMENT_INCOMPLETE.value
    if any(mapping.reason_code.value == incomplete for mapping in mappings):
        return incomplete
    return None
