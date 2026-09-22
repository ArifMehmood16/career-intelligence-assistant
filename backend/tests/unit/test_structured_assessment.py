"""PLAN 13D.3 — a structured assessment decides support.

Lexical and embedding signals still retrieve evidence. They do not decide that
a requirement is met, including when they agree. A missing, refused, truncated
or malformed assessment stays incomplete and never becomes a match.
"""

from __future__ import annotations

import json

from career_assistant.adapters.relatedness.model import ModelAdjudicator
from career_assistant.application.analysis.relatedness import map_role_requirements
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)
from career_assistant.domain.assessment import parse_assessments
from career_assistant.domain.claims import Claim
from career_assistant.domain.mapping import MappingReason, MappingStatus
from career_assistant.domain.requirements import Requirement

_COURSE = "Completed an introductory Python course."
_LEADERSHIP = "Five years leading production Python systems."


class _ScriptedCompletion:
    def __init__(
        self,
        payload: dict[str, object] | str,
        *,
        structured: bool,
    ) -> None:
        self._payload = payload
        self.calls = 0
        self.last_request: CompletionRequest | None = None
        self._structured = structured

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="scripted",
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=self._structured,
            context_window_tokens=8192,
            max_output_tokens=2048,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self.calls += 1
        self.last_request = request
        text = (
            self._payload
            if isinstance(self._payload, str)
            else json.dumps(self._payload)
        )
        return CompletionResult(
            text=text,
            provider_id="scripted",
            model_tag="scripted-v1",
            left_machine=False,
        )


def _requirement() -> Requirement:
    return Requirement(
        id="req-python-leadership",
        text=_LEADERSHIP,
        competency="python",
        seniority_signal="lead",
        must_have=True,
        source_span_id="span-jd",
        extraction_confidence=1.0,
        is_vague=False,
    )


def _claims() -> tuple[Claim, Claim]:
    return (
        Claim(
            id="claim-course",
            competency="python",
            context=_COURSE,
            duration_signal="course",
            recency_signal="recent",
            source_span_ids=("span-course",),
            extraction_confidence=1.0,
        ),
        Claim(
            id="claim-negation",
            competency="python",
            context="This was not production leadership.",
            duration_signal="course",
            recency_signal="recent",
            source_span_ids=("span-negation",),
            extraction_confidence=1.0,
        ),
    )


def _met_payload(*span_ids: str) -> dict[str, object]:
    return {
        "assessments": [
            {
                "requirementId": "req-python-leadership",
                "assessment": "met",
                "supportingSpanIds": list(span_ids),
                "unmetConditions": [],
                "unknownConditions": [],
                "contradiction": False,
                "justification": "The cited span supports the requirement.",
            }
        ]
    }


def test_agreement_without_an_assessment_is_not_a_match() -> None:
    completion = _ScriptedCompletion("not-json", structured=True)
    mappings = map_role_requirements(
        (_requirement(),),
        _claims(),
        similarities={
            ("req-python-leadership", "claim-course"): 0.9,
            ("req-python-leadership", "claim-negation"): 0.1,
        },
        adjudicator=ModelAdjudicator(completion),
        similarity_floor=0.55,
    )
    assert completion.calls == 1
    assert mappings[0].status is MappingStatus.MISSING
    assert mappings[0].reason_code is MappingReason.ASSESSMENT_INCOMPLETE
    assert mappings[0].justifying_span_ids == ()
    request = completion.last_request
    assert request is not None
    assert request.json_schema is not None
    assert "evidence-assessment-v3" in request.system
    assert "UNTRUSTED_REQUIREMENT" in request.user
    assert "span-negation" in request.user


def test_model_met_for_a_course_does_not_meet_leadership() -> None:
    """PLAN 13D.5 — a validated met on a course still does not score as leadership."""
    completion = _ScriptedCompletion(_met_payload("span-course"), structured=True)
    mappings = map_role_requirements(
        (_requirement(),),
        _claims(),
        similarities={("req-python-leadership", "claim-course"): 0.9},
        adjudicator=ModelAdjudicator(completion),
        similarity_floor=0.55,
    )
    assert completion.calls == 1
    assert mappings[0].status is MappingStatus.MISSING
    assert mappings[0].justifying_span_ids == ()


def test_prompted_json_path_validates_the_same_payload() -> None:
    production = Claim(
        id="claim-course",
        competency="python",
        context="Led production Python systems for five years.",
        duration_signal="5y",
        recency_signal="recent",
        source_span_ids=("span-course",),
        extraction_confidence=1.0,
    )
    completion = _ScriptedCompletion(_met_payload("span-course"), structured=False)
    mappings = map_role_requirements(
        (_requirement(),),
        (production,),
        similarities={("req-python-leadership", "claim-course"): 0.9},
        adjudicator=ModelAdjudicator(completion),
        similarity_floor=0.55,
    )
    assert mappings[0].status is MappingStatus.MET
    assert mappings[0].justifying_span_ids == ("span-course",)
    request = completion.last_request
    assert request is not None
    assert request.json_schema is None
    assert "requirementId" in request.system


def test_unknown_span_refusal_and_truncation_do_not_match() -> None:
    allowed = {"req-python-leadership": frozenset({"span-course"})}
    forged = parse_assessments(_met_payload("span-forged"), allowed=allowed)
    assert forged == {}
    contradicted = parse_assessments(
        {
            "assessments": [
                {
                    "requirementId": "req-python-leadership",
                    "assessment": "met",
                    "supportingSpanIds": ["span-course"],
                    "unmetConditions": [],
                    "unknownConditions": [],
                    "contradiction": True,
                    "justification": "The letter denies the CV.",
                }
            ]
        },
        allowed=allowed,
    )
    assert contradicted == {}
    duplicated = parse_assessments(
        {
            "assessments": [
                _met_payload("span-course")["assessments"][0],
                _met_payload("span-course")["assessments"][0],
            ]
        },
        allowed=allowed,
    )
    assert duplicated == {}
    assert parse_assessments('{"assessments": [', allowed=allowed) == {}
    assert parse_assessments("I must refuse.", allowed=allowed) == {}


def test_the_assessment_prompt_states_what_each_level_means() -> None:
    """A level with no definition is decided by the model's disposition.

    On the live pilot no labelled `met` came back as `met`, and unrelated
    requirements came back `partial`. The prompt named the three levels and
    defined none of them, so both directions were unconstrained.
    """
    completion = _ScriptedCompletion("not-json", structured=True)
    map_role_requirements(
        (_requirement(),),
        _claims(),
        similarities={("req-python-leadership", "claim-course"): 0.9},
        adjudicator=ModelAdjudicator(completion),
        similarity_floor=0.55,
    )

    request = completion.last_request
    assert request is not None
    assert "evidence-assessment-v3" in request.system
    for level in ("met:", "partial:", "missing:"):
        assert level in request.system, level
    assert "unsure" in request.system
    # The one gate failure on the capable model: two cited passages disagreed
    # and it answered met without setting the flag, so the rule is stated as a
    # rule rather than trailing the paragraph.
    assert "disagree" in request.system
