"""Deterministic fit scoring — pure functions over mappings and a rubric."""

from __future__ import annotations

import re
from dataclasses import dataclass

from career_assistant.domain.claims import Claim
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.requirements import Requirement


@dataclass(frozen=True, slots=True)
class ScoringRubric:
    weight_must_have: float
    weight_desirable: float
    status_met: float
    status_partial: float
    status_missing: float
    recency_recent: float
    recency_mid: float
    recency_old: float
    band_strong_min: float
    band_partial_min: float


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    requirement_id: str
    must_have: bool
    status: MappingStatus
    weight: float
    status_factor: float
    recency_factor: float
    contribution: float
    adjudicated: bool = False


@dataclass(frozen=True, slots=True)
class ScoreExplanation:
    score: float
    band: str
    components: tuple[ScoreComponent, ...]
    denominator: float
    numerator: float


def score_fit(
    requirements: tuple[Requirement, ...] | list[Requirement],
    mappings: tuple[RequirementMapping, ...] | list[RequirementMapping],
    claims: tuple[Claim, ...] | list[Claim],
    rubric: ScoringRubric,
) -> ScoreExplanation:
    by_id = {r.id: r for r in requirements}
    claims_by_id = {c.id: c for c in claims}
    components: list[ScoreComponent] = []
    numerator = 0.0
    denominator = 0.0

    counted = _score_once_ids(requirements, mappings)
    incomplete = any(
        mapping.reason_code is MappingReason.ASSESSMENT_INCOMPLETE
        for mapping in mappings
    )
    for mapping in mappings:
        req = by_id[mapping.requirement_id]
        weight = rubric.weight_must_have if req.must_have else rubric.weight_desirable
        if mapping.requirement_id not in counted:
            weight = 0.0
        status_factor = _coverage_factor(mapping, rubric)
        recency_factor = _recency_factor(mapping, claims_by_id, rubric)
        contribution = weight * status_factor * recency_factor
        numerator += contribution
        denominator += weight
        components.append(
            ScoreComponent(
                requirement_id=req.id,
                must_have=req.must_have,
                status=mapping.status,
                weight=weight,
                status_factor=status_factor,
                recency_factor=recency_factor,
                contribution=contribution,
                adjudicated=mapping.signals.adjudication is True,
            )
        )

    if denominator <= 0:
        return ScoreExplanation(
            score=0.0,
            band="unscored",
            components=tuple(components),
            denominator=denominator,
            numerator=numerator,
        )
    score = 100.0 * numerator / denominator
    score = max(0.0, min(100.0, score))
    band = "incomplete" if incomplete and score == 0.0 else _band(score, rubric)
    return ScoreExplanation(
        score=score,
        band=band,
        components=tuple(components),
        denominator=denominator,
        numerator=numerator,
    )


def counterfactual_delta(
    requirements: tuple[Requirement, ...] | list[Requirement],
    mappings: tuple[RequirementMapping, ...] | list[RequirementMapping],
    claims: tuple[Claim, ...] | list[Claim],
    rubric: ScoringRubric,
    *,
    requirement_id: str,
) -> float:
    """Score lift if ``requirement_id`` were met with recent evidence."""
    baseline = score_fit(requirements, mappings, claims, rubric)
    adjusted: list[RequirementMapping] = []
    for mapping in mappings:
        if mapping.requirement_id == requirement_id:
            adjusted.append(
                RequirementMapping(
                    requirement_id=mapping.requirement_id,
                    status=MappingStatus.MET,
                    reason_code=mapping.reason_code,
                    justifying_span_ids=mapping.justifying_span_ids,
                    justifying_claim_ids=mapping.justifying_claim_ids,
                )
            )
        else:
            adjusted.append(mapping)
    # Force recent factor via a synthetic claim when none justify.
    claims_list = list(claims)
    if not any(
        m.requirement_id == requirement_id and m.justifying_claim_ids for m in adjusted
    ):
        synthetic = Claim(
            id=f"cf-{requirement_id}",
            competency="general",
            context="counterfactual recent evidence",
            duration_signal="1y",
            recency_signal="recent",
            source_span_ids=(f"cf-span-{requirement_id}",),
            extraction_confidence=1.0,
        )
        claims_list.append(synthetic)
        adjusted = [
            RequirementMapping(
                requirement_id=m.requirement_id,
                status=m.status,
                reason_code=MappingReason.MATCHED
                if m.requirement_id == requirement_id
                else m.reason_code,
                justifying_span_ids=synthetic.source_span_ids
                if m.requirement_id == requirement_id
                else m.justifying_span_ids,
                justifying_claim_ids=(synthetic.id,)
                if m.requirement_id == requirement_id
                else m.justifying_claim_ids,
            )
            for m in adjusted
        ]
    hypothetical = score_fit(requirements, adjusted, claims_list, rubric)
    return hypothetical.score - baseline.score


_SPACE = re.compile(r"\s+")


def _score_once_ids(
    requirements: tuple[Requirement, ...] | list[Requirement],
    mappings: tuple[RequirementMapping, ...] | list[RequirementMapping],
) -> set[str]:
    """Identical requirement text counts once. The strongest mapping is kept."""
    by_id = {requirement.id: requirement for requirement in requirements}
    groups: dict[tuple[str, bool, str], list[RequirementMapping]] = {}
    order: list[tuple[str, bool, str]] = []
    for mapping in mappings:
        requirement = by_id[mapping.requirement_id]
        key = (
            _SPACE.sub(" ", requirement.text.casefold()).strip(),
            requirement.must_have,
            requirement.item_type.value,
        )
        if key not in groups:
            order.append(key)
        groups.setdefault(key, []).append(mapping)
    kept: set[str] = set()
    for key in order:
        group = groups[key]
        best = min(
            group,
            key=lambda item: (_status_rank(item.status), item.requirement_id),
        )
        kept.add(best.requirement_id)
    return kept


def _status_rank(status: MappingStatus) -> int:
    if status is MappingStatus.MET:
        return 0
    if status is MappingStatus.PARTIAL:
        return 1
    return 2


def _coverage_factor(mapping: RequirementMapping, rubric: ScoringRubric) -> float:
    factor = _status_factor(mapping.status, rubric)
    if mapping.unknown_conditions or mapping.contradiction:
        return min(factor, rubric.status_partial)
    return factor


def _status_factor(status: MappingStatus, rubric: ScoringRubric) -> float:
    if status is MappingStatus.MET:
        return rubric.status_met
    if status is MappingStatus.PARTIAL:
        return rubric.status_partial
    return rubric.status_missing


def _recency_factor(
    mapping: RequirementMapping,
    claims_by_id: dict[str, Claim],
    rubric: ScoringRubric,
) -> float:
    if mapping.status is MappingStatus.MISSING or not mapping.justifying_claim_ids:
        return 1.0
    claim = claims_by_id.get(mapping.justifying_claim_ids[0])
    if claim is None:
        return 1.0
    if claim.recency_signal == "recent":
        return rubric.recency_recent
    if claim.recency_signal == "mid":
        return rubric.recency_mid
    if claim.recency_signal == "old":
        return rubric.recency_old
    # undated: do not invent recency — treat as mid penalty (documented neutral)
    return rubric.recency_mid


def _band(score: float, rubric: ScoringRubric) -> str:
    if score >= rubric.band_strong_min:
        return "strong"
    if score >= rubric.band_partial_min:
        return "partial"
    return "limited"
