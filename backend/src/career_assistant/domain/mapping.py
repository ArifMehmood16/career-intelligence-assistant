"""Requirement-to-claim mapping — pure domain policy, no I/O."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from career_assistant.domain.claims import Claim
from career_assistant.domain.recency import covered_years, stated_years
from career_assistant.domain.relatedness import RelatednessSignals, pair_relatedness
from career_assistant.domain.requirements import Requirement


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


def map_requirements(
    requirements: tuple[Requirement, ...] | list[Requirement],
    claims: tuple[Claim, ...] | list[Claim],
    *,
    similarities: Mapping[tuple[str, str], float] | None = None,
    adjudications: Mapping[tuple[str, str], bool] | None = None,
    similarity_floor: float = 0.55,
) -> tuple[RequirementMapping, ...]:
    # Benefits, logistics and explicit non-requirements are kept and shown, but
    # a candidate is never mapped or scored against them. Self-authored cover
    # letter claims are narrative: citable, never evidence for a mapping.
    evidence = tuple(claim for claim in claims if not claim.self_authored)
    return tuple(
        map_requirement(
            req,
            evidence,
            similarities=similarities,
            adjudications=adjudications,
            similarity_floor=similarity_floor,
        )
        for req in requirements
        if req.is_scoreable
    )


def map_requirement(
    requirement: Requirement,
    claims: tuple[Claim, ...] | list[Claim],
    *,
    similarities: Mapping[tuple[str, str], float] | None = None,
    adjudications: Mapping[tuple[str, str], bool] | None = None,
    similarity_floor: float = 0.55,
) -> RequirementMapping:
    """Map one requirement to met/partial/missing with a reason and span ids."""
    sims = similarities or {}
    adjs = adjudications or {}
    considered: list[tuple[Claim, RelatednessSignals]] = []
    related: list[tuple[Claim, RelatednessSignals]] = []
    for claim in claims:
        key = (requirement.id, claim.id)
        signals = pair_relatedness(
            requirement,
            claim,
            similarity=sims.get(key, 0.0),
            similarity_floor=similarity_floor,
            adjudication=adjs[key] if key in adjs else None,
        )
        considered.append((claim, signals))
        if signals.related:
            related.append((claim, signals))
    if not related:
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.MISSING,
            reason_code=MappingReason.NO_RELATED_CLAIM,
            justifying_span_ids=(),
            justifying_claim_ids=(),
            signals=_closest_miss(considered),
        )

    same = [(c, s) for c, s in related if c.competency == requirement.competency]
    if not same:
        best, best_signals = _best_claim(related)
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.PARTIAL,
            reason_code=MappingReason.ADJACENT_CLAIM_ONLY,
            justifying_span_ids=best.source_span_ids,
            justifying_claim_ids=(best.id,),
            signals=best_signals,
        )

    recent_enough = [
        item for item in same if item[0].recency_signal in {"recent", "mid", "undated"}
    ]
    pool = recent_enough or same
    best, best_signals = _best_claim(pool)
    if not recent_enough and all(c.recency_signal == "old" for c, _s in same):
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.PARTIAL,
            reason_code=MappingReason.EVIDENCE_TOO_OLD,
            justifying_span_ids=best.source_span_ids,
            justifying_claim_ids=(best.id,),
            signals=best_signals,
        )

    if best_signals.lexical_overlap < 1 and requirement.competency == "general":
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.PARTIAL,
            reason_code=MappingReason.EVIDENCE_THIN,
            justifying_span_ids=best.source_span_ids,
            justifying_claim_ids=(best.id,),
            signals=best_signals,
        )

    matched = RequirementMapping(
        requirement_id=requirement.id,
        status=MappingStatus.MET,
        reason_code=MappingReason.MATCHED,
        justifying_span_ids=best.source_span_ids,
        justifying_claim_ids=(best.id,),
        signals=best_signals,
    )
    return limit_concurrent_years(
        requirement, tuple(claim for claim, _signals in pool), matched
    )


def limit_concurrent_years(
    requirement: Requirement,
    claims: tuple[Claim, ...] | list[Claim],
    mapping: RequirementMapping,
) -> RequirementMapping:
    """Do not treat overlapping jobs as separate years of coverage."""
    if mapping.status is not MappingStatus.MET:
        return mapping
    needed = stated_years(requirement.text)
    if needed is None:
        return mapping
    dated = tuple(
        claim
        for claim in claims
        if claim.period_start is not None and claim.competency == requirement.competency
    )
    covered = covered_years(dated)
    # Calendar spans land a fraction under a whole year. A month of slack
    # keeps back-to-back jobs that add up, and still rejects a real gap.
    if covered is None or covered >= needed - (1 / 12):
        return mapping
    span_ids = tuple(
        dict.fromkeys(span_id for claim in dated for span_id in claim.source_span_ids)
    )
    return RequirementMapping(
        requirement_id=mapping.requirement_id,
        status=MappingStatus.PARTIAL,
        reason_code=MappingReason.EVIDENCE_THIN,
        justifying_span_ids=span_ids or mapping.justifying_span_ids,
        justifying_claim_ids=tuple(claim.id for claim in dated),
        signals=mapping.signals,
        unknown_conditions=mapping.unknown_conditions,
        contradiction=mapping.contradiction,
    )


def _best_claim(
    items: list[tuple[Claim, RelatednessSignals]],
) -> tuple[Claim, RelatednessSignals]:
    rank = {"recent": 0, "mid": 1, "undated": 2, "old": 3}

    def key(item: tuple[Claim, RelatednessSignals]) -> tuple[int, int]:
        claim = item[0]
        return (rank.get(claim.recency_signal, 9), -len(claim.context))

    return sorted(items, key=key)[0]


def _closest_miss(
    items: list[tuple[Claim, RelatednessSignals]],
) -> RelatednessSignals:
    """Keep the strongest rejected pair so a veto still shows on the mapping."""
    if not items:
        return RelatednessSignals()
    return max(
        items,
        key=lambda item: (item[1].embedding_similarity, item[1].lexical_overlap),
    )[1]
