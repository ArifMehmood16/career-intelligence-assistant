"""Application-layer relatedness: gather the three signals, domain combines."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from career_assistant.application.ports.adjudication import (
    AdjudicationPair,
    AdjudicationPort,
)
from career_assistant.domain.claims import Claim
from career_assistant.domain.mapping import RequirementMapping, map_requirements
from career_assistant.domain.relatedness import lexical_overlap
from career_assistant.domain.requirements import Requirement


def disagreement_pairs(
    requirements: Sequence[Requirement],
    claims: Sequence[Claim],
    *,
    similarities: Mapping[tuple[str, str], float],
    similarity_floor: float,
) -> tuple[AdjudicationPair, ...]:
    """Pairs where lexical overlap and embedding cosine disagree.

    Agreement (both related or both not) is already decided. Cover-letter
    claims and unscoreable items never reach the model.
    """
    pairs: list[AdjudicationPair] = []
    for requirement in requirements:
        if not requirement.is_scoreable:
            continue
        for claim in claims:
            if claim.self_authored:
                continue
            similarity = similarities.get((requirement.id, claim.id), 0.0)
            lexical = lexical_overlap(requirement.text, claim.context) >= 1
            embedding = similarity >= similarity_floor
            if lexical == embedding:
                continue
            pairs.append(
                AdjudicationPair(
                    requirement_id=requirement.id,
                    claim_id=claim.id,
                    requirement_text=requirement.text,
                    claim_context=claim.context,
                )
            )
    return tuple(pairs)


class NullAdjudicator:
    """Hermetic default: no model call. Domain falls back to OR on disagreement."""

    def adjudicate(
        self, pairs: Sequence[AdjudicationPair]
    ) -> Mapping[tuple[str, str], bool]:
        return {}


def map_role_requirements(
    requirements: Sequence[Requirement],
    claims: Sequence[Claim],
    *,
    similarities: Mapping[tuple[str, str], float] | None = None,
    adjudicator: AdjudicationPort,
    similarity_floor: float,
) -> tuple[RequirementMapping, ...]:
    sims = similarities or {}
    pairs = disagreement_pairs(
        requirements,
        claims,
        similarities=sims,
        similarity_floor=similarity_floor,
    )
    adjudications: Mapping[tuple[str, str], bool] = (
        adjudicator.adjudicate(pairs) if pairs else {}
    )
    return map_requirements(
        tuple(requirements),
        tuple(claims),
        similarities=sims,
        adjudications=adjudications,
        similarity_floor=similarity_floor,
    )
