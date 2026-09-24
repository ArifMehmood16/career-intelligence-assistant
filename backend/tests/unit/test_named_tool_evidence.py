"""A skills line meets a requirement that only names that tool."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from career_assistant.application.analysis.relatedness import map_role_requirements
from career_assistant.application.ports.adjudication import AssessmentItem
from career_assistant.domain.assessment import EvidenceAssessment
from career_assistant.domain.claims import LISTED_DURATION, Claim
from career_assistant.domain.mapping import MappingStatus, map_requirement
from career_assistant.domain.requirements import Requirement

_SKILLS = (
    "Python, TypeScript, AWS, PostgreSQL, CI/CD, Event-driven & distributed systems"
)


def _requirement(text: str, *, seniority: str | None = None) -> Requirement:
    return Requirement(
        id="req",
        text=text,
        competency="general",
        seniority_signal=seniority,
        must_have=True,
        source_span_id="req-span",
        extraction_confidence=0.9,
        is_vague=False,
    )


def _listed(context: str = _SKILLS) -> Claim:
    return Claim(
        id="listed",
        competency="skills",
        context=context,
        duration_signal=LISTED_DURATION,
        recency_signal="undated",
        source_span_ids=("skills-span",),
        extraction_confidence=0.8,
    )


def _work(context: str) -> Claim:
    return Claim(
        id="work",
        competency="python",
        context=context,
        duration_signal="2y",
        recency_signal="recent",
        source_span_ids=("work-span",),
        extraction_confidence=0.9,
    )


def test_a_skills_line_meets_a_named_tool() -> None:
    result = map_requirement(_requirement("Python"), (_listed(),))

    assert result.status is MappingStatus.MET
    assert result.justifying_span_ids == ("skills-span",)


def test_a_skills_line_does_not_meet_years_of_leadership() -> None:
    result = map_requirement(
        _requirement(
            "Five years leading production Python systems",
            seniority="five_years_leadership",
        ),
        (_listed(),),
    )

    assert result.status is MappingStatus.MISSING
    assert result.justifying_span_ids == ()


def test_a_skills_line_does_not_meet_a_soft_requirement() -> None:
    result = map_requirement(_requirement("Strong communication"), (_listed(),))

    assert result.status is MappingStatus.MISSING
    assert result.justifying_span_ids == ()


def test_a_work_bullet_is_the_citation_when_it_names_the_tool() -> None:
    result = map_requirement(
        _requirement("Python"),
        (_listed(), _work("Built production services in Python.")),
    )

    assert result.status is MappingStatus.MET
    assert result.justifying_span_ids == ("work-span",)


class _RecordingAssessor:
    def __init__(self) -> None:
        self.requirement_ids: list[str] = []

    @property
    def decides_support(self) -> bool:
        return True

    def assess(
        self, items: Sequence[AssessmentItem]
    ) -> Mapping[str, EvidenceAssessment]:
        self.requirement_ids = [item.requirement_id for item in items]
        return {
            item.requirement_id: EvidenceAssessment(
                requirement_id=item.requirement_id,
                status="met",
                supporting_span_ids=tuple(
                    span_id
                    for evidence in item.evidence
                    for span_id in evidence.span_ids
                ),
                unmet_conditions=(),
                unknown_conditions=(),
                contradiction=False,
                justification="The cited work shows the requirement.",
            )
            for item in items
        }


def test_the_assessor_is_not_asked_about_a_named_tool() -> None:
    """A listed tool is already decided. A responsibility still needs assessment."""
    python = _requirement("Python")
    python = Requirement(
        id="python",
        text=python.text,
        competency=python.competency,
        seniority_signal=None,
        must_have=True,
        source_span_id="span-python",
        extraction_confidence=0.9,
        is_vague=False,
    )
    stack = Requirement(
        id="stack",
        text="Contributing across the stack where required (TypeScript)",
        competency="typescript",
        seniority_signal=None,
        must_have=True,
        source_span_id="span-stack",
        extraction_confidence=0.9,
        is_vague=False,
    )
    assessor = _RecordingAssessor()
    mappings = map_role_requirements(
        (python, stack),
        (
            _listed(),
            _work("Built TypeScript services across the web and device API."),
        ),
        adjudicator=assessor,
        similarity_floor=0.55,
    )
    by_id = {mapping.requirement_id: mapping for mapping in mappings}

    assert by_id["python"].status is MappingStatus.MET
    assert by_id["python"].justifying_span_ids == ("skills-span",)
    assert assessor.requirement_ids == ["stack"]


def test_short_tool_names_match_and_a_synonym_does_not() -> None:
    listed = _listed()
    assert map_requirement(_requirement("AWS"), (listed,)).status is MappingStatus.MET
    assert map_requirement(_requirement("CI/CD"), (listed,)).status is MappingStatus.MET
    kafka = _listed("Kafka, SQS")
    event_driven = map_requirement(
        _requirement("Event-driven & distributed systems"),
        (kafka,),
    )
    assert event_driven.status is MappingStatus.MISSING
    assert (
        map_requirement(
            _requirement("Event-driven & distributed systems"),
            (listed,),
        ).status
        is MappingStatus.MET
    )
