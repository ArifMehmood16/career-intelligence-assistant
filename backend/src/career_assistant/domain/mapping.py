"""Requirement-to-claim mapping — pure domain policy, no I/O."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from career_assistant.domain.claims import Claim
from career_assistant.domain.requirements import Requirement

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "for",
        "with",
        "on",
        "in",
        "of",
        "to",
        "by",
        "at",
        "from",
        "experience",
        "strong",
        "production",
        "owned",
        "wrote",
        "built",
        "used",
    }
)


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


@dataclass(frozen=True, slots=True)
class RequirementMapping:
    requirement_id: str
    status: MappingStatus
    reason_code: MappingReason
    justifying_span_ids: tuple[str, ...]
    justifying_claim_ids: tuple[str, ...]


def map_requirements(
    requirements: tuple[Requirement, ...] | list[Requirement],
    claims: tuple[Claim, ...] | list[Claim],
    *,
    similarities: Mapping[tuple[str, str], float] | None = None,
) -> tuple[RequirementMapping, ...]:
    return tuple(
        map_requirement(req, claims, similarities=similarities) for req in requirements
    )


def map_requirement(
    requirement: Requirement,
    claims: tuple[Claim, ...] | list[Claim],
    *,
    similarities: Mapping[tuple[str, str], float] | None = None,
    similarity_floor: float = 0.55,
) -> RequirementMapping:
    """Map one requirement to met/partial/missing with a reason and span ids."""
    sims = similarities or {}
    related = [
        claim
        for claim in claims
        if _is_related(
            requirement,
            claim,
            sims.get((requirement.id, claim.id), 0.0),
            similarity_floor,
        )
    ]
    if not related:
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.MISSING,
            reason_code=MappingReason.NO_RELATED_CLAIM,
            justifying_span_ids=(),
            justifying_claim_ids=(),
        )

    same = [c for c in related if c.competency == requirement.competency]
    if not same:
        best = _best_claim(related)
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.PARTIAL,
            reason_code=MappingReason.ADJACENT_CLAIM_ONLY,
            justifying_span_ids=best.source_span_ids,
            justifying_claim_ids=(best.id,),
        )

    recent_enough = [
        c for c in same if c.recency_signal in {"recent", "mid", "undated"}
    ]
    pool = recent_enough or same
    best = _best_claim(pool)
    if not recent_enough and all(c.recency_signal == "old" for c in same):
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.PARTIAL,
            reason_code=MappingReason.EVIDENCE_TOO_OLD,
            justifying_span_ids=best.source_span_ids,
            justifying_claim_ids=(best.id,),
        )

    if (
        _overlap_count(requirement.text, best.context) < 1
        and requirement.competency == "general"
    ):
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.PARTIAL,
            reason_code=MappingReason.EVIDENCE_THIN,
            justifying_span_ids=best.source_span_ids,
            justifying_claim_ids=(best.id,),
        )

    return RequirementMapping(
        requirement_id=requirement.id,
        status=MappingStatus.MET,
        reason_code=MappingReason.MATCHED,
        justifying_span_ids=best.source_span_ids,
        justifying_claim_ids=(best.id,),
    )


def _is_related(
    requirement: Requirement,
    claim: Claim,
    similarity: float,
    similarity_floor: float,
) -> bool:
    if claim.competency == requirement.competency:
        return True
    if _overlap_count(requirement.text, claim.context) >= 1:
        return True
    # Embeddings may propose adjacent candidates lexical overlap misses.
    return similarity >= similarity_floor


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 2}


def _overlap_count(left: str, right: str) -> int:
    return len(_tokens(left) & _tokens(right))


def _best_claim(claims: list[Claim]) -> Claim:
    rank = {"recent": 0, "mid": 1, "undated": 2, "old": 3}

    def key(claim: Claim) -> tuple[int, int]:
        return (rank.get(claim.recency_signal, 9), -len(claim.context))

    return sorted(claims, key=key)[0]
