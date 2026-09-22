"""PLAN 13D.5 — an incomplete assessment is not the same result as a poor fit."""

from __future__ import annotations

from career_assistant.domain.attribution import analysis_failure_status
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)


def _mapping(reason: MappingReason) -> RequirementMapping:
    return RequirementMapping(
        requirement_id="req-1",
        status=MappingStatus.MISSING,
        reason_code=reason,
        justifying_span_ids=(),
        justifying_claim_ids=(),
    )


def test_incomplete_assessment_is_recorded_apart_from_a_poor_fit() -> None:
    incomplete = _mapping(MappingReason.ASSESSMENT_INCOMPLETE)
    poor_fit = _mapping(MappingReason.NO_RELATED_CLAIM)

    assert analysis_failure_status((incomplete,)) == "assessment_incomplete"
    assert analysis_failure_status((poor_fit,)) is None
    assert analysis_failure_status((poor_fit, incomplete)) == "assessment_incomplete"
