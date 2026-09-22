"""PLAN 13D — retrieval must be visible and must not gate the assessor.

The live pilot returned `missing` for requirements whose supporting claim was
never put in front of the model. A disagreement is only informative once the
retrieved set is recorded, so every mapping carries what the assessor saw.
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
from career_assistant.domain.claims import Claim
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
