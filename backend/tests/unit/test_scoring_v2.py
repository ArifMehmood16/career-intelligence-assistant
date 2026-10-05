"""Scoring v2: pure aggregation of validated verdicts (ADR 014, PLAN 18.9).

No database and no model: verdicts are value objects, and the rubric is the
configured `scoring-rubric-v2`.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from career_assistant.application.scoring.rubric_loader import (
    load_scoring_rubric_v2,
)
from career_assistant.domain.candidate_facts import (
    CandidateFacts,
    Coverage,
    TermFact,
)
from career_assistant.domain.experience import ExperienceFact
from career_assistant.domain.judging import JudgedVerdict, ProposedQuote, ProposedScore
from career_assistant.domain.recency import DateRange
from career_assistant.domain.scoring_v2 import (
    Dimension,
    RequirementToScore,
    gap_plan,
    keyword_coverage,
    score_v2,
)

RUBRIC_PATH = Path(__file__).resolve().parents[3] / "config" / "scoring_rubric.toml"
RUBRIC = load_scoring_rubric_v2(RUBRIC_PATH)
AS_OF = date(2026, 9, 1)
RECENT = DateRange(date(2024, 1, 1), None)
OLD = DateRange(date(2010, 1, 1), date(2014, 1, 1))


def _verdict(
    requirement_id: str,
    match: int,
    *,
    experience: int | None = None,
    seniority: int | None = None,
) -> JudgedVerdict:
    label = "missing" if match <= 1 else ("met" if match >= 3 else "partial")
    return JudgedVerdict(
        requirement_id=requirement_id,
        verdict=label,
        match_score=match,
        match_rationale="r",
        evidence=(ProposedQuote("c1", "q"),) if match else (),
        seniority=None if seniority is None else ProposedScore(seniority, "r"),
        experience=None if experience is None else ProposedScore(experience, "r"),
        unmet_conditions=(),
        contradiction=False,
        sufficient=True,
        rewrite_query=None,
        adjustments=(),
    )


def _item(
    requirement_id: str,
    match: int,
    *,
    must_have: bool = True,
    dates: tuple[DateRange | None, ...] = (RECENT,),
    **dimensions: int,
) -> RequirementToScore:
    return RequirementToScore(
        requirement_id=requirement_id,
        must_have=must_have,
        verdict=_verdict(requirement_id, match, **dimensions),
        cited_dates=dates,
    )


def test_the_configured_rubric_is_the_current_v2_rubric() -> None:
    assert RUBRIC.version == "scoring-rubric-v2"
    assert (RUBRIC.w_match, RUBRIC.w_experience, RUBRIC.w_seniority) == (0.5, 0.3, 0.2)


def test_every_requirement_met_as_stated_recently_scores_100() -> None:
    result = score_v2(
        [_item("r1", 3, experience=3, seniority=3), _item("r2", 3)],
        rubric=RUBRIC,
        as_of=AS_OF,
    )

    assert result.publishable
    assert result.score == pytest.approx(100.0)
    assert result.band == "strong"


def test_only_the_dimensions_a_requirement_states_count() -> None:
    result = score_v2([_item("r1", 3, experience=0)], rubric=RUBRIC, as_of=AS_OF)

    # (0.5 * 3 + 0.3 * 0) / (3 * 0.8)
    assert result.score == pytest.approx(100 * 1.5 / 2.4)


def test_a_4_earns_no_bonus_even_inside_its_own_requirement() -> None:
    result = score_v2([_item("r1", 4, experience=2)], rubric=RUBRIC, as_of=AS_OF)

    # (0.5 * 3 + 0.3 * 2) / (3 * 0.8), not full credit
    assert result.score == pytest.approx(100 * 2.1 / 2.4)
    assert result.components[0].dimension_scores[Dimension.MATCH] == 4


def test_a_missing_verdict_scores_zero_whatever_its_other_dimensions() -> None:
    result = score_v2(
        [_item("r1", 1, experience=3), _item("r2", 3)], rubric=RUBRIC, as_of=AS_OF
    )

    assert result.components[0].requirement_score == 0.0
    assert result.score == pytest.approx(50.0)


def test_must_haves_weigh_three_times_a_desirable() -> None:
    result = score_v2(
        [_item("r1", 3), _item("r2", 0, must_have=False)], rubric=RUBRIC, as_of=AS_OF
    )

    assert result.score == pytest.approx(75.0)


def test_recency_follows_the_latest_dated_cited_chunk() -> None:
    items = [
        _item("old", 3, dates=(OLD,)),
        _item("mixed", 3, dates=(OLD, RECENT, None)),
        _item("undated", 3, dates=(None,)),
    ]

    result = score_v2(items, rubric=RUBRIC, as_of=AS_OF)

    factors = {c.requirement_id: c.recency_factor for c in result.components}
    assert factors == {"old": 0.7, "mixed": 1.0, "undated": 0.85}


def test_a_missing_must_have_caps_the_band_at_partial() -> None:
    items = [_item(f"r{i}", 3) for i in range(4)] + [_item("gap", 0)]

    result = score_v2(items, rubric=RUBRIC, as_of=AS_OF)

    assert result.score == pytest.approx(80.0)
    assert (result.band, result.gated) == ("partial", True)


def test_a_missing_desirable_does_not_gate_the_band() -> None:
    items = [_item(f"r{i}", 3) for i in range(4)] + [_item("nice", 0, must_have=False)]

    result = score_v2(items, rubric=RUBRIC, as_of=AS_OF)

    assert (result.band, result.gated) == ("strong", False)


def test_an_incomplete_analysis_publishes_no_score_band_or_components() -> None:
    result = score_v2([_item("r1", 3)], incomplete=("r2",), rubric=RUBRIC, as_of=AS_OF)

    assert result.publishable is False
    assert (result.score, result.band, result.components) == (None, "incomplete", ())


def test_no_requirements_is_unscored() -> None:
    result = score_v2([], rubric=RUBRIC, as_of=AS_OF)

    assert (result.publishable, result.score, result.band) == (False, None, "unscored")


def test_keyword_coverage_is_reported_beside_the_score() -> None:
    none = ExperienceFact(0, 0, 0, None, ongoing=False)
    facts = CandidateFacts(
        terms=(
            TermFact("pgvector", Coverage.EXACT, none),
            TermFact("postgresql", Coverage.ALIAS, none),
            TermFact("qdrant", Coverage.MISSING, none),
        ),
        roles=(),
    )

    coverage = keyword_coverage(facts)

    assert coverage.exact == ("pgvector",)
    assert coverage.alias == ("postgresql",)
    assert coverage.missing == ("qdrant",)


def test_the_gap_plan_orders_by_score_delta_and_names_the_dimension() -> None:
    items = [
        _item("years", 3, experience=1),
        _item("absent", 0),
        _item("junior", 3, seniority=2),
        _item("done", 3),
    ]

    plan = gap_plan(items, rubric=RUBRIC, as_of=AS_OF)

    assert [(g.requirement_id, g.dimension) for g in plan] == [
        ("absent", Dimension.MATCH),
        ("years", Dimension.EXPERIENCE),
        ("junior", Dimension.SENIORITY),
    ]
    assert plan[0].delta > plan[1].delta > plan[2].delta > 0
    assert plan[0].current == 0


def test_old_evidence_is_a_recency_gap() -> None:
    plan = gap_plan([_item("stale", 3, dates=(OLD,))], rubric=RUBRIC, as_of=AS_OF)

    assert [(g.requirement_id, g.dimension) for g in plan] == [
        ("stale", Dimension.RECENCY)
    ]


def test_an_incomplete_analysis_has_no_gap_plan() -> None:
    assert (
        gap_plan([_item("r1", 0)], incomplete=("r2",), rubric=RUBRIC, as_of=AS_OF) == ()
    )


def test_scoring_is_deterministic_and_order_independent() -> None:
    items = [_item("a", 2), _item("b", 3, experience=1), _item("c", 0)]

    forward = score_v2(items, rubric=RUBRIC, as_of=AS_OF)
    backward = score_v2(list(reversed(items)), rubric=RUBRIC, as_of=AS_OF)

    assert forward.score == backward.score
    assert replace(forward, components=()) == replace(backward, components=())
