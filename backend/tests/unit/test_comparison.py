"""Phase 13A.7 — comparison differentiator is a real status distinction."""

from __future__ import annotations

from career_assistant.domain.comparison import compare_requirement_sets
from career_assistant.domain.mapping import MappingReason, MappingStatus, RequirementMapping
from career_assistant.domain.requirements import Requirement


def _requirement(
    *,
    req_id: str,
    text: str,
    must_have: bool = True,
) -> Requirement:
    return Requirement(
        id=req_id,
        text=text,
        competency="skill",
        seniority_signal=None,
        must_have=must_have,
        source_span_id="span-1",
        extraction_confidence=0.9,
        is_vague=False,
    )


def _mapping(req_id: str, status: MappingStatus) -> RequirementMapping:
    return RequirementMapping(
        requirement_id=req_id,
        status=status,
        reason_code=MappingReason.MATCHED,
        justifying_span_ids=(),
        justifying_claim_ids=(),
    )


def test_differentiator_is_status_mismatch_not_first_shared_alphabetically() -> None:
    result = compare_requirement_sets(
        title_a="Analytics Engineer",
        title_b="Platform Engineer",
        requirements_a=(
            _requirement(req_id="a-looker", text="Aardvark observability"),
            _requirement(req_id="a-sql", text="SQL warehousing skills"),
        ),
        mappings_a=(
            _mapping("a-looker", MappingStatus.MISSING),
            _mapping("a-sql", MappingStatus.MET),
        ),
        requirements_b=(
            _requirement(req_id="b-looker", text="Aardvark observability"),
            _requirement(req_id="b-sql", text="SQL warehousing skills"),
        ),
        mappings_b=(
            _mapping("b-looker", MappingStatus.MISSING),
            _mapping("b-sql", MappingStatus.MISSING),
        ),
    )

    assert result.shared[0].text == "Aardvark observability"
    assert "Aardvark" not in result.differentiator
    assert "SQL warehousing skills" in result.differentiator
    assert "met" in result.differentiator
    assert "missing" in result.differentiator
