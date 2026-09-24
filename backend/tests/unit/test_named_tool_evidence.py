"""A skills line meets a requirement that only names that tool."""

from __future__ import annotations

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
