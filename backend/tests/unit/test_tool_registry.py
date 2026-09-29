"""The ask registry exposes the eight read-only tools and returns verbatim text."""

from __future__ import annotations

from career_assistant.application.ask.registry import TOOL_NAMES, evidence_registry
from career_assistant.domain.ask import RoleAnalysisView
from career_assistant.domain.documents import DocumentKind, Span
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.prompts import RetrievedSpan
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoreComponent, ScoreExplanation


def _view() -> RoleAnalysisView:
    requirement = Requirement(
        id="dbt",
        text="Production dbt experience",
        competency="dbt",
        seniority_signal=None,
        must_have=True,
        source_span_id="jd-dbt",
        extraction_confidence=0.9,
        is_vague=False,
    )
    return RoleAnalysisView(
        role_id="role-1",
        title="Analytics Engineer",
        explanation=ScoreExplanation(
            score=0.0,
            band="limited",
            components=(
                ScoreComponent(
                    requirement_id="dbt",
                    must_have=True,
                    status=MappingStatus.MISSING,
                    weight=3.0,
                    status_factor=0.0,
                    recency_factor=1.0,
                    contribution=0.0,
                ),
            ),
            denominator=3.0,
            numerator=0.0,
        ),
        requirements=(requirement,),
        mappings=(
            RequirementMapping(
                requirement_id="dbt",
                status=MappingStatus.MISSING,
                reason_code=MappingReason.NO_RELATED_CLAIM,
                justifying_span_ids=("span-1",),
                justifying_claim_ids=(),
            ),
        ),
        span_texts={"span-1": "Owned dbt models in production."},
    )


def _pool() -> tuple[RetrievedSpan, ...]:
    return (
        RetrievedSpan(
            span=Span(
                id="span-1",
                document_id="doc-1",
                page_number=1,
                start_offset=0,
                end_offset=32,
                text="Owned dbt models in production.",
            ),
            document_kind=DocumentKind.CV,
        ),
    )


def test_the_registry_lists_the_eight_read_only_tools() -> None:
    registry = evidence_registry((_view(),), _pool())

    assert tuple(tool.name for tool in registry.tools) == TOOL_NAMES
    assert all(tool.read_only for tool in registry.tools)
    assert [item.name for item in registry.definitions()] == list(TOOL_NAMES)


def test_search_returns_the_span_verbatim() -> None:
    registry = evidence_registry((_view(),), _pool())

    found = registry.call("search_evidence", {"query": "dbt models"})

    assert found.chunks == (("span-1", "Owned dbt models in production."),)
    assert "Owned dbt models in production." in found.output


def test_an_unknown_tool_and_bad_input_are_errors() -> None:
    registry = evidence_registry((_view(),), _pool())

    assert "unknown_tool" in registry.call("delete_role", {}).output
    assert "invalid_input" in registry.call("search_evidence", {}).output


def test_the_gap_plan_lists_the_unmet_requirement() -> None:
    registry = evidence_registry((_view(),), _pool())

    plan = registry.call("get_gap_plan", {"role_id": "role-1"})

    assert "dbt" in plan.output
    assert "missing" in plan.output


_CALLS: dict[str, dict[str, object]] = {
    "list_roles": {},
    "search_evidence": {"query": "dbt"},
    "get_role_analysis": {"role_id": "role-1"},
    "explain_requirement": {"requirement_id": "dbt"},
    "get_gap_plan": {"role_id": "role-1"},
    "compare_roles": {"role_id_a": "role-1", "role_id_b": "role-1"},
    "skill_experience": {"term": "dbt"},
    "get_chunk": {"chunk_id": "span-1"},
}


def test_every_tool_output_matches_its_declared_schema() -> None:
    registry = evidence_registry((_view(),), _pool())
    assert set(_CALLS) == set(TOOL_NAMES)

    for tool in registry.tools:
        run = registry.call(tool.name, _CALLS[tool.name])
        assert run.error is None, tool.name
        tool.output_model.model_validate_json(run.output)


def test_a_failed_call_names_its_error_for_the_caller() -> None:
    registry = evidence_registry((_view(),), _pool())

    assert registry.call("get_role_analysis", {"role_id": "nope"}).error == (
        "role_not_found"
    )
    assert registry.call("get_chunk", {"chunk_id": "nope"}).error == ("chunk_not_found")
    assert registry.call("delete_role", {}).error == "unknown_tool"
    assert registry.call("search_evidence", {}).error == "invalid_input"
