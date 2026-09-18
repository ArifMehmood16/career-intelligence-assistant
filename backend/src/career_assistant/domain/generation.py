"""Deterministic generation artefacts — gap plan first; drafts use groundedness."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from career_assistant.domain.claims import Claim
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import (
    ScoringRubric,
    counterfactual_delta,
    score_fit,
)


class GapAction(StrEnum):
    EVIDENCE_IT = "evidence_it"
    LEARN_IT = "learn_it"
    ACCEPT_IT = "accept_it"


@dataclass(frozen=True, slots=True)
class GapItem:
    requirement_id: str
    requirement_text: str
    must_have: bool
    status: MappingStatus
    reason_code: MappingReason
    score_delta: float
    action: GapAction
    adjacent_claim_ids: tuple[str, ...]
    can_draft_bullet: bool


@dataclass(frozen=True, slots=True)
class GapPlan:
    current_score: float
    items: tuple[GapItem, ...]


def build_gap_plan(
    requirements: tuple[Requirement, ...] | list[Requirement],
    mappings: tuple[RequirementMapping, ...] | list[RequirementMapping],
    claims: tuple[Claim, ...] | list[Claim],
    rubric: ScoringRubric,
) -> GapPlan:
    """Order non-met requirements by counterfactual score lift. Pure, no model."""
    by_id = {r.id: r for r in requirements}
    baseline = score_fit(requirements, mappings, claims, rubric)
    items: list[GapItem] = []
    for mapping in mappings:
        if mapping.status is MappingStatus.MET:
            continue
        req = by_id[mapping.requirement_id]
        delta = counterfactual_delta(
            requirements,
            mappings,
            claims,
            rubric,
            requirement_id=req.id,
        )
        adjacent = mapping.justifying_claim_ids
        action = _action_for(mapping, req)
        items.append(
            GapItem(
                requirement_id=req.id,
                requirement_text=req.text,
                must_have=req.must_have,
                status=mapping.status,
                reason_code=mapping.reason_code,
                score_delta=delta,
                action=action,
                adjacent_claim_ids=adjacent,
                can_draft_bullet=bool(adjacent) and action is GapAction.EVIDENCE_IT,
            )
        )
    items.sort(key=lambda item: (-item.score_delta, item.requirement_id))
    return GapPlan(current_score=baseline.score, items=tuple(items))


def _action_for(mapping: RequirementMapping, req: Requirement) -> GapAction:
    if mapping.reason_code is MappingReason.ADJACENT_CLAIM_ONLY or (
        mapping.status is MappingStatus.PARTIAL and mapping.justifying_claim_ids
    ):
        return GapAction.EVIDENCE_IT
    if not req.must_have and mapping.status is MappingStatus.MISSING:
        return GapAction.ACCEPT_IT
    return GapAction.LEARN_IT
