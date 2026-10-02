"""Phase 10.3 — deterministic gap plan ordered by scoreDelta (no model)."""

from __future__ import annotations

from tests.support.published_analysis import mappings_fixture, published_scores

from career_assistant.domain.claims import Claim
from career_assistant.domain.generation import GapAction, build_gap_plan
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.requirements import Requirement


def _req(id: str, text: str, *, must_have: bool = True) -> Requirement:
    return Requirement(
        id=id,
        text=text,
        competency=id,
        seniority_signal=None,
        must_have=must_have,
        source_span_id=f"jd-{id}",
        extraction_confidence=0.9,
        is_vague=False,
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


def test_gap_plan_orders_by_score_delta_descending() -> None:
    requirements = (
        _req("dbt", "Production dbt"),
        _req("cuda", "CUDA experience"),
        _req("looker", "Looker dashboards", must_have=False),
    )
    claims = (_claim("c1", "dbt", "Owned dbt models in production."),)
    mappings = mappings_fixture(requirements, claims)
    plan = build_gap_plan(
        requirements,
        mappings,
        explanation=published_scores(requirements, mappings)[0],
        gaps=published_scores(requirements, mappings)[1],
    )
    assert [item.requirement_id for item in plan.items] == ["cuda", "looker"]
    assert plan.items[0].score_delta >= plan.items[1].score_delta
    assert plan.items[0].status is MappingStatus.MISSING
    assert plan.items[0].reason_code is MappingReason.NO_RELATED_CLAIM


def test_gap_plan_action_evidence_it_when_adjacent_claim_exists() -> None:
    requirements = (_req("airflow", "Production Airflow ownership"),)
    mappings = (
        RequirementMapping(
            requirement_id="airflow",
            status=MappingStatus.PARTIAL,
            reason_code=MappingReason.ADJACENT_CLAIM_ONLY,
            justifying_span_ids=("cv-c1",),
            justifying_claim_ids=("c1",),
        ),
    )
    plan = build_gap_plan(
        requirements,
        mappings,
        explanation=published_scores(requirements, mappings)[0],
        gaps=published_scores(requirements, mappings)[1],
    )
    assert len(plan.items) == 1
    assert plan.items[0].action is GapAction.EVIDENCE_IT
    assert plan.items[0].adjacent_claim_ids == ("c1",)
    assert plan.items[0].can_draft_bullet is False


def test_gap_plan_excludes_met_requirements() -> None:
    requirements = (_req("dbt", "Production dbt"),)
    claims = (_claim("c1", "dbt", "Owned dbt models in production."),)
    mappings = mappings_fixture(requirements, claims)
    plan = build_gap_plan(
        requirements,
        mappings,
        explanation=published_scores(requirements, mappings)[0],
        gaps=published_scores(requirements, mappings)[1],
    )
    assert plan.items == ()


def test_gap_plan_is_deterministic() -> None:
    requirements = (
        _req("cuda", "CUDA"),
        _req("ros", "ROS2"),
    )
    claims = ()
    mappings = mappings_fixture(requirements, claims)
    a = build_gap_plan(
        requirements,
        mappings,
        explanation=published_scores(requirements, mappings)[0],
        gaps=published_scores(requirements, mappings)[1],
    )
    b = build_gap_plan(
        requirements,
        mappings,
        explanation=published_scores(requirements, mappings)[0],
        gaps=published_scores(requirements, mappings)[1],
    )
    assert a == b
