"""Synthetic published verdict fixtures for generation-domain tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from career_assistant.application.scoring.rubric_loader import load_scoring_rubric_v2
from career_assistant.domain.claims import Claim
from career_assistant.domain.judging import JudgedVerdict, ProposedQuote
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoreComponent, ScoreExplanation
from career_assistant.domain.scoring_v2 import (
    Gap,
    RequirementToScore,
    gap_plan,
    score_v2,
)

RUBRIC = load_scoring_rubric_v2(
    Path(__file__).resolve().parents[3] / "config/scoring_rubric.toml"
)
AS_OF = date(2026, 9, 1)


def mappings_fixture(
    requirements: tuple[Requirement, ...], claims: tuple[Claim, ...]
) -> tuple[RequirementMapping, ...]:
    """Fixture statuses, with one example claim for each named competency."""
    result = []
    for req in requirements:
        claim = next((c for c in claims if c.competency == req.competency), None)
        result.append(
            RequirementMapping(
                requirement_id=req.id,
                status=MappingStatus.MET if claim else MappingStatus.MISSING,
                reason_code=MappingReason.MATCHED
                if claim
                else MappingReason.NO_RELATED_CLAIM,
                justifying_span_ids=claim.source_span_ids if claim else (),
                justifying_claim_ids=(claim.id,) if claim else (),
            )
        )
    return tuple(result)


def published_scores(
    requirements: tuple[Requirement, ...], mappings: tuple[RequirementMapping, ...]
) -> tuple[ScoreExplanation, tuple[Gap, ...]]:
    by_id = {m.requirement_id: m for m in mappings}
    items = []
    for req in requirements:
        if not req.is_scoreable:
            continue
        mapping = by_id[req.id]
        score = {
            MappingStatus.MET: 3,
            MappingStatus.PARTIAL: 2,
            MappingStatus.MISSING: 0,
        }[mapping.status]
        verdict = JudgedVerdict(
            requirement_id=req.id,
            verdict=mapping.status.value,
            match_score=score,
            match_rationale="Validated fixture",
            evidence=tuple(
                ProposedQuote(s, "fixture quote") for s in mapping.justifying_span_ids
            ),
            seniority=None,
            experience=None,
            unmet_conditions=(),
            contradiction=False,
            sufficient=True,
            rewrite_query=None,
            adjustments=(),
        )
        items.append(RequirementToScore(req.id, req.must_have, verdict, (None,)))
    fit = score_v2(items, rubric=RUBRIC, as_of=AS_OF)
    components = tuple(
        ScoreComponent(
            c.requirement_id,
            c.must_have,
            by_id[c.requirement_id].status,
            c.weight,
            c.requirement_score,
            c.recency_factor,
            c.contribution,
            True,
        )
        for c in fit.components
    )
    explanation = ScoreExplanation(
        fit.score or 0,
        fit.band,
        components,
        sum(c.weight for c in fit.components),
        sum(c.contribution for c in fit.components),
        fit.publishable,
    )
    return explanation, gap_plan(items, rubric=RUBRIC, as_of=AS_OF)
