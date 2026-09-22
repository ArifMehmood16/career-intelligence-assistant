"""PLAN 13D — retrieval must be visible and must not gate the assessor.

The live pilot returned `missing` for requirements whose supporting claim was
never put in front of the model. A disagreement is only informative once the
retrieved set is recorded, so every mapping carries what the assessor saw.
"""

from __future__ import annotations

import json

import pytest

from career_assistant.adapters.relatedness.model import ModelAdjudicator
from career_assistant.application.analysis import relatedness
from career_assistant.application.analysis.relatedness import map_role_requirements
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)
from career_assistant.domain.claims import Claim
from career_assistant.domain.mapping import MappingReason, MappingStatus
from career_assistant.domain.requirements import Requirement

_REQUIREMENT_ID = "req-dba"


class _ScriptedCompletion:
    """Records the prompt so a test can compare it with the recorded retrieval."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.calls = 0
        self.last_request: CompletionRequest | None = None

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="scripted",
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=8192,
            max_output_tokens=2048,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self.calls += 1
        self.last_request = request
        return CompletionResult(
            text=json.dumps(self._payload),
            provider_id="scripted",
            model_tag="scripted-v1",
            left_machine=False,
        )


def _requirement() -> Requirement:
    return Requirement(
        id=_REQUIREMENT_ID,
        text="Experience administering relational databases.",
        competency="databases",
        seniority_signal=None,
        must_have=True,
        source_span_id="span-jd",
        extraction_confidence=1.0,
        is_vague=False,
    )


def _claim(claim_id: str, context: str, span_id: str) -> Claim:
    return Claim(
        id=claim_id,
        competency="databases",
        context=context,
        duration_signal="3y",
        recency_signal="recent",
        source_span_ids=(span_id,),
        extraction_confidence=1.0,
    )


def _claims() -> tuple[Claim, ...]:
    return (
        _claim(
            "claim-databases",
            "Administering relational databases for three years.",
            "span-databases",
        ),
        _claim("claim-neighbour", "Owned the nightly backup rota.", "span-neighbour"),
        _claim("claim-unrelated", "Ran the weekly design review.", "span-unrelated"),
    )


def _missing_payload() -> dict[str, object]:
    return {
        "assessments": [
            {
                "requirementId": _REQUIREMENT_ID,
                "assessment": "missing",
                "supportingSpanIds": [],
                "unmetConditions": [],
                "unknownConditions": [],
                "contradiction": False,
                "justification": "No cited span supports the requirement.",
            }
        ]
    }


def test_a_mapping_records_the_evidence_put_in_front_of_the_assessor() -> None:
    completion = _ScriptedCompletion(_missing_payload())
    claims = _claims()
    mappings = map_role_requirements(
        (_requirement(),),
        claims,
        similarities={(_REQUIREMENT_ID, "claim-databases"): 0.9},
        adjudicator=ModelAdjudicator(completion),
        similarity_floor=0.55,
    )

    retrieved = mappings[0].retrieved_claim_ids
    assert retrieved, "the assessor was called, so something was retrieved"
    request = completion.last_request
    assert request is not None
    for claim in claims:
        shown = all(span_id in request.user for span_id in claim.source_span_ids)
        assert (claim.id in retrieved) is shown, claim.id


def test_a_paraphrase_below_the_floor_still_reaches_the_assessor() -> None:
    """A gate on lexical overlap or the floor decides `missing` before the model."""
    completion = _ScriptedCompletion(_missing_payload())
    paraphrase = _claim(
        "claim-paraphrase",
        "Looked after the company's Postgres estate.",
        "span-paraphrase",
    )
    other = _claim("claim-other", "Ran the weekly design review.", "span-other")
    mappings = map_role_requirements(
        (_requirement(),),
        (paraphrase, other),
        similarities={
            (_REQUIREMENT_ID, "claim-paraphrase"): 0.42,
            (_REQUIREMENT_ID, "claim-other"): 0.03,
        },
        adjudicator=ModelAdjudicator(completion),
        similarity_floor=0.55,
    )

    assert completion.calls == 1, "the requirement was never assessed"
    request = completion.last_request
    assert request is not None
    assert "span-paraphrase" in request.user
    assert "claim-paraphrase" in mappings[0].retrieved_claim_ids


def test_the_candidate_set_stays_bounded() -> None:
    """Retrieval proposes a shortlist. It does not hand over the whole CV."""
    completion = _ScriptedCompletion(_missing_payload())
    contexts = (
        "Administered relational databases for three years.",
        "Tuned query plans on the reporting replica.",
        "Owned the nightly backup rota.",
        "Migrated a legacy schema without downtime.",
        "Set up connection pooling for the platform.",
        "Wrote the runbook for failover drills.",
        "Chaired the weekly design review.",
        "Mentored two graduate engineers.",
        "Presented at an internal brown bag.",
        "Organised the team offsite.",
        "Kept the meeting notes for the guild.",
        "Judged the summer hackathon.",
    )
    claims = tuple(
        _claim(f"claim-{index:02d}", text, f"span-{index:02d}")
        for index, text in enumerate(contexts)
    )
    scores = (0.90, 0.80, 0.70, 0.65, 0.60)
    similarities = {
        (_REQUIREMENT_ID, claim.id): (scores[index] if index < len(scores) else 0.05)
        for index, claim in enumerate(claims)
    }
    mappings = map_role_requirements(
        (_requirement(),),
        claims,
        similarities=similarities,
        adjudicator=ModelAdjudicator(completion),
        similarity_floor=0.55,
    )

    retrieved = mappings[0].retrieved_claim_ids
    assert len(retrieved) < len(claims)
    assert "claim-11" not in retrieved
    request = completion.last_request
    assert request is not None
    assert "span-11" not in request.user


def test_the_lexical_path_never_decides_when_an_assessor_is_in_charge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No eligible evidence is a recorded outcome, not a silent fall back."""

    def _forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("the lexical path decided a requirement")

    monkeypatch.setattr(relatedness, "map_requirements", _forbidden)
    completion = _ScriptedCompletion(_missing_payload())
    letter = Claim(
        id="claim-letter",
        competency="databases",
        context="I would relish the chance to run a database estate.",
        duration_signal="none",
        recency_signal="recent",
        source_span_ids=("span-letter",),
        extraction_confidence=1.0,
        self_authored=True,
    )

    mappings = map_role_requirements(
        (_requirement(),),
        (letter,),
        similarities={},
        adjudicator=ModelAdjudicator(completion),
        similarity_floor=0.55,
    )

    assert completion.calls == 0
    assert mappings[0].status is MappingStatus.MISSING
    assert mappings[0].reason_code is MappingReason.NO_RELATED_CLAIM
    assert mappings[0].retrieved_claim_ids == ()
    assert mappings[0].justifying_span_ids == ()


def _letter(claim_id: str, context: str, span_id: str) -> Claim:
    return Claim(
        id=claim_id,
        competency="databases",
        context=context,
        duration_signal="none",
        recency_signal="recent",
        source_span_ids=(span_id,),
        extraction_confidence=1.0,
        self_authored=True,
    )


def test_a_letter_that_denies_the_cv_is_visible_but_cannot_support() -> None:
    """A denial the assessor never sees is a contradiction it cannot report.

    Self-authored text is not candidate evidence and never awards a match. It
    still has to be in front of the assessor, or a letter saying the work was
    not done reads as agreement.
    """
    completion = _ScriptedCompletion(_missing_payload())
    cv = _claim(
        "claim-databases",
        "Administered relational databases for three years.",
        "span-databases",
    )
    denial = _letter(
        "claim-denial",
        "I have not administered a database and the earlier line should not count.",
        "span-denial",
    )

    mappings = map_role_requirements(
        (_requirement(),),
        (cv, denial),
        similarities={(_REQUIREMENT_ID, "claim-databases"): 0.9},
        adjudicator=ModelAdjudicator(completion),
        similarity_floor=0.55,
    )

    request = completion.last_request
    assert request is not None
    assert "span-denial" in request.user
    assert "claim-denial" in mappings[0].retrieved_claim_ids
    assert mappings[0].status is MappingStatus.MISSING


def test_a_match_cited_only_to_self_authored_text_is_not_accepted() -> None:
    """The letter is context. A citation of it cannot be the support for a match."""
    payload = {
        "assessments": [
            {
                "requirementId": _REQUIREMENT_ID,
                "assessment": "met",
                "supportingSpanIds": ["span-denial"],
                "unmetConditions": [],
                "unknownConditions": [],
                "contradiction": False,
                "justification": "The letter mentions databases.",
            }
        ]
    }
    completion = _ScriptedCompletion(payload)
    cv = _claim(
        "claim-databases",
        "Administered relational databases for three years.",
        "span-databases",
    )
    denial = _letter(
        "claim-denial",
        "I have not administered a database and the earlier line should not count.",
        "span-denial",
    )

    mappings = map_role_requirements(
        (_requirement(),),
        (cv, denial),
        similarities={(_REQUIREMENT_ID, "claim-databases"): 0.9},
        adjudicator=ModelAdjudicator(completion),
        similarity_floor=0.55,
    )

    assert mappings[0].status is MappingStatus.MISSING
    assert mappings[0].reason_code is MappingReason.ASSESSMENT_INCOMPLETE
    assert mappings[0].justifying_span_ids == ()
