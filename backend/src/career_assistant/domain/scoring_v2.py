"""Scoring v2: pure aggregation of validated verdicts (ADR 014, PLAN 18.9).

For each requirement, the applicable dimensions — match always, experience and
seniority when the requirement states them — are weighted with 3 as full credit,
then multiplied by the recency of the latest dated cited chunk. A missing verdict
scores 0. The fit score weights must-haves against desirables; a must-have that is
missing caps the band at partial. The model never produces any of these numbers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from career_assistant.domain.candidate_facts import CandidateFacts, Coverage
from career_assistant.domain.judging import JudgedVerdict
from career_assistant.domain.recency import DateRange, derive_recency_signal


class Dimension(StrEnum):
    MATCH = "match"
    EXPERIENCE = "experience"
    SENIORITY = "seniority"
    RECENCY = "recency"


@dataclass(frozen=True, slots=True)
class RubricV2:
    version: str
    w_match: float
    w_experience: float
    w_seniority: float
    weight_must_have: float
    weight_desirable: float
    recency_recent: float
    recency_mid: float
    recency_old: float
    recency_undated: float
    band_strong_min: float
    band_partial_min: float
    gate_match_max: int


@dataclass(frozen=True, slots=True)
class RequirementToScore:
    requirement_id: str
    must_have: bool
    verdict: JudgedVerdict
    cited_dates: tuple[DateRange | None, ...]


@dataclass(frozen=True, slots=True)
class RequirementScore:
    requirement_id: str
    must_have: bool
    weight: float
    dimension_scores: Mapping[Dimension, int]
    recency_factor: float
    requirement_score: float
    contribution: float


@dataclass(frozen=True, slots=True)
class FitScoreV2:
    score: float | None
    band: str
    publishable: bool
    gated: bool
    components: tuple[RequirementScore, ...]


@dataclass(frozen=True, slots=True)
class KeywordCoverage:
    exact: tuple[str, ...]
    alias: tuple[str, ...]
    missing: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Gap:
    requirement_id: str
    dimension: Dimension
    current: float
    delta: float


FULL_CREDIT = 3
_INCOMPLETE = FitScoreV2(None, "incomplete", False, False, ())
_UNSCORED = FitScoreV2(None, "unscored", False, False, ())
_LIFTS = (Dimension.MATCH, Dimension.EXPERIENCE, Dimension.SENIORITY)


def score_v2(
    items: Sequence[RequirementToScore],
    *,
    rubric: RubricV2,
    as_of: date,
    incomplete: Sequence[str] = (),
) -> FitScoreV2:
    """An incomplete analysis publishes nothing — never a low score."""
    if incomplete:
        return _INCOMPLETE
    if not items:
        return _UNSCORED
    components = tuple(
        _component(
            item, _dimensions(item.verdict), _recency(item, rubric, as_of), rubric
        )
        for item in sorted(items, key=lambda i: i.requirement_id)
    )
    score = _fit(components)
    gated = any(
        item.must_have and item.verdict.match_score <= rubric.gate_match_max
        for item in items
    )
    band = _band(score, rubric)
    if gated and band == "strong":
        band = "partial"
    return FitScoreV2(score, band, True, gated, components)


def keyword_coverage(facts: CandidateFacts) -> KeywordCoverage:
    """Beside the score, not in it: the judge already reads these facts."""

    def named(coverage: Coverage) -> tuple[str, ...]:
        return tuple(t.term for t in facts.terms if t.coverage is coverage)

    return KeywordCoverage(
        exact=named(Coverage.EXACT),
        alias=named(Coverage.ALIAS),
        missing=named(Coverage.MISSING),
    )


def gap_plan(
    items: Sequence[RequirementToScore],
    *,
    rubric: RubricV2,
    as_of: date,
    incomplete: Sequence[str] = (),
) -> tuple[Gap, ...]:
    """Each requirement's single biggest lift, largest score delta first."""
    baseline = score_v2(items, rubric=rubric, as_of=as_of, incomplete=incomplete)
    if not baseline.publishable:
        return ()
    total = sum(c.weight for c in baseline.components)
    by_id = {item.requirement_id: item for item in items}
    gaps = [
        gap
        for component in baseline.components
        if (
            gap := _best_lift(by_id[component.requirement_id], component, total, rubric)
        )
    ]
    return tuple(sorted(gaps, key=lambda g: (-g.delta, g.requirement_id)))


def _best_lift(
    item: RequirementToScore,
    component: RequirementScore,
    total_weight: float,
    rubric: RubricV2,
) -> Gap | None:
    best: Gap | None = None
    for dimension, lifted, recency, current in _lifts(component):
        raised = _component(item, lifted, recency, rubric).contribution
        delta = 100.0 * (raised - component.contribution) / total_weight
        if delta > 1e-9 and (best is None or delta > best.delta + 1e-9):
            best = Gap(item.requirement_id, dimension, current, delta)
    return best


_Lift = tuple[Dimension, Mapping[Dimension, int], float, float]


def _lifts(component: RequirementScore) -> list[_Lift]:
    scores = component.dimension_scores
    missing = scores[Dimension.MATCH] <= 1
    # A missing requirement has no evidence to date; v1 lifts it as recent.
    recency = 1.0 if missing else component.recency_factor
    lifts: list[_Lift] = [
        (
            dimension,
            {**scores, dimension: FULL_CREDIT},
            recency,
            float(scores[dimension]),
        )
        for dimension in _LIFTS
        if dimension in scores and scores[dimension] < FULL_CREDIT
    ]
    if not missing and component.recency_factor < 1.0:
        lifts.append((Dimension.RECENCY, scores, 1.0, component.recency_factor))
    return lifts


def _dimensions(verdict: JudgedVerdict) -> dict[Dimension, int]:
    scores = {Dimension.MATCH: verdict.match_score}
    if verdict.experience_score is not None:
        scores[Dimension.EXPERIENCE] = verdict.experience_score
    if verdict.seniority_score is not None:
        scores[Dimension.SENIORITY] = verdict.seniority_score
    return scores


def _component(
    item: RequirementToScore,
    scores: Mapping[Dimension, int],
    recency: float,
    rubric: RubricV2,
) -> RequirementScore:
    weight = rubric.weight_must_have if item.must_have else rubric.weight_desirable
    requirement = 0.0
    if scores[Dimension.MATCH] > 1:
        weights = {
            Dimension.MATCH: rubric.w_match,
            Dimension.EXPERIENCE: rubric.w_experience,
            Dimension.SENIORITY: rubric.w_seniority,
        }
        # A 4 is shown but earns no bonus, even against its own requirement.
        earned = sum(weights[d] * min(s, FULL_CREDIT) for d, s in scores.items())
        possible = FULL_CREDIT * sum(weights[d] for d in scores)
        requirement = earned / possible * recency
    return RequirementScore(
        requirement_id=item.requirement_id,
        must_have=item.must_have,
        weight=weight,
        dimension_scores=dict(scores),
        recency_factor=recency,
        requirement_score=requirement,
        contribution=weight * requirement,
    )


def _recency(item: RequirementToScore, rubric: RubricV2, as_of: date) -> float:
    dated = [span for span in item.cited_dates if span is not None]
    if not dated:
        return rubric.recency_undated
    latest = max(dated, key=lambda span: span.end or as_of)
    factors = {
        "recent": rubric.recency_recent,
        "mid": rubric.recency_mid,
        "old": rubric.recency_old,
    }
    return factors[derive_recency_signal(latest, as_of=as_of)]


def _fit(components: Sequence[RequirementScore]) -> float:
    total = sum(c.weight for c in components)
    return 100.0 * sum(c.contribution for c in components) / total


def _band(score: float, rubric: RubricV2) -> str:
    if score >= rubric.band_strong_min:
        return "strong"
    if score >= rubric.band_partial_min:
        return "partial"
    return "limited"
