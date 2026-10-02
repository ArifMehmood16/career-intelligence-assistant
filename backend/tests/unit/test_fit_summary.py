"""PLAN 13C.8 — a prose fit summary names the strongest and weakest requirements."""

from __future__ import annotations

from tests.support.published_analysis import mappings_fixture, published_scores

from career_assistant.domain.claims import Claim
from career_assistant.domain.generation import build_fit_summary
from career_assistant.domain.requirements import ItemType, Requirement


def _req(
    id: str,
    text: str,
    *,
    competency: str | None = None,
    must_have: bool = True,
    item_type: ItemType = ItemType.REQUIREMENT,
) -> Requirement:
    return Requirement(
        id=id,
        text=text,
        competency=competency or id,
        seniority_signal=None,
        must_have=must_have,
        source_span_id=f"jd-{id}",
        extraction_confidence=0.9,
        is_vague=False,
        item_type=item_type,
    )


def _claim(id: str, competency: str, context: str) -> Claim:
    return Claim(
        id=id,
        competency=competency,
        context=context,
        duration_signal="2y",
        recency_signal="recent",
        source_span_ids=(f"cv-{id}",),
        extraction_confidence=0.9,
    )


def test_fit_summary_names_strongest_match_and_biggest_gap() -> None:
    requirements = (
        _req("dbt", "Production dbt experience", competency="dbt"),
        _req("cuda", "CUDA kernel authoring", competency="cuda"),
    )
    claims = (_claim("c1", "dbt", "Owned dbt models in production."),)
    mappings = mappings_fixture(requirements, claims)
    summary = build_fit_summary(
        requirements,
        mappings,
        explanation=published_scores(requirements, mappings)[0],
        gaps=published_scores(requirements, mappings)[1],
    )
    assert summary.strongest_requirement_id == "dbt"
    assert summary.weakest_requirement_id == "cuda"
    assert "Production dbt experience" in summary.text
    assert "CUDA kernel authoring" in summary.text


def test_fit_summary_ignores_unscoreable_items() -> None:
    requirements = (
        _req("dbt", "Production dbt experience", competency="dbt"),
        _req(
            "pay",
            "Salary 70,000 to 80,000",
            competency="general",
            item_type=ItemType.BENEFIT,
        ),
    )
    claims = (_claim("c1", "dbt", "Owned dbt models in production."),)
    mappings = mappings_fixture(requirements, claims)
    summary = build_fit_summary(
        requirements,
        mappings,
        explanation=published_scores(requirements, mappings)[0],
        gaps=published_scores(requirements, mappings)[1],
    )
    assert "Salary" not in summary.text
    assert summary.strongest_requirement_id == "dbt"


def test_fit_summary_when_nothing_is_met() -> None:
    requirements = (_req("cuda", "CUDA kernel authoring", competency="cuda"),)
    mappings = mappings_fixture(requirements, ())
    summary = build_fit_summary(
        requirements, mappings,
        explanation=published_scores(requirements, mappings)[0],
        gaps=published_scores(requirements, mappings)[1],
    )
    assert summary.strongest_requirement_id is None
    assert summary.weakest_requirement_id == "cuda"
    assert "CUDA kernel authoring" in summary.text
