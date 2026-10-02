"""Requirement-to-claim mapping — pure domain policy, no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from career_assistant.domain.relatedness import RelatednessSignals


class MappingStatus(StrEnum):
    MET = "met"
    PARTIAL = "partial"
    MISSING = "missing"


class MappingReason(StrEnum):
    NO_RELATED_CLAIM = "no_related_claim"
    ADJACENT_CLAIM_ONLY = "adjacent_claim_only"
    EVIDENCE_TOO_OLD = "evidence_too_old"
    EVIDENCE_THIN = "evidence_thin"
    MATCHED = "matched"
    ASSESSMENT_INCOMPLETE = "assessment_incomplete"


@dataclass(frozen=True, slots=True)
class RequirementMapping:
    requirement_id: str
    status: MappingStatus
    reason_code: MappingReason
    justifying_span_ids: tuple[str, ...]
    justifying_claim_ids: tuple[str, ...]
    signals: RelatednessSignals = field(default_factory=RelatednessSignals)
    # Unknown or conflicting evidence is not full coverage. Scoring reads these;
    # a citation still does not prove the requirement is met.
    unknown_conditions: tuple[str, ...] = ()
    contradiction: bool = False
    # What the assessor was actually shown. A `missing` result means nothing
    # until this says whether the supporting claim was ever in the prompt.
    retrieved_claim_ids: tuple[str, ...] = ()
