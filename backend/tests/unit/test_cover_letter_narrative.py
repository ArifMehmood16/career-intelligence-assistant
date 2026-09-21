"""PLAN 13C.4 — an uploaded cover letter is narrative, never score evidence.

A cover letter is extracted into the same structured claim shape and flagged
self-authored. It stays excluded from mappings and the fit score (4.3, 5.7,
6.5). Spans remain citable for Ask and drafting.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from career_assistant.adapters.extraction.claims_model import ModelClaimExtractor
from career_assistant.adapters.extraction.claims_rules import RulesClaimExtractor
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric
from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.mapping import MappingStatus, map_requirements
from career_assistant.domain.normalisation import normalise_text
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import score_fit

AS_OF = date(2026, 9, 18)
ROOT = Path(__file__).resolve().parents[3]
RUBRIC = load_scoring_rubric(ROOT / "config" / "scoring_rubric.toml")

LETTER = normalise_text(
    "I am writing to apply.\n"
    "- I have production dbt experience on Snowflake.\n"
    "- I led CUDA kernel work for the warehouse.\n"
)


class _ScriptedCompletion:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="scripted",
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=8192,
            max_output_tokens=1024,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        return CompletionResult(
            text=json.dumps(self._payload),
            provider_id="scripted",
            model_tag="scripted-v1",
            left_machine=False,
        )


def _req() -> Requirement:
    return Requirement(
        id="r1",
        text="Production dbt experience",
        competency="dbt",
        seniority_signal=None,
        must_have=True,
        source_span_id="span-r1",
        extraction_confidence=0.9,
        is_vague=False,
    )


def test_rules_extract_cover_letter_bullets_as_self_authored() -> None:
    result = RulesClaimExtractor(as_of=AS_OF).extract(
        document_id="doc-cl",
        document_kind=DocumentKind.COVER_LETTER,
        normalised_text=LETTER,
    )

    assert result.claims
    assert all(c.self_authored for c in result.claims)
    assert any("dbt" in c.context.lower() for c in result.claims)


def test_model_extracts_a_cover_letter_as_self_authored() -> None:
    payload = {
        "roles": [
            {
                "employer": "",
                "title": "",
                "date_range_quote": "",
                "claims": [
                    {
                        "quote": "I have production dbt experience on Snowflake.",
                        "competency": "dbt",
                    }
                ],
            }
        ]
    }
    result = ModelClaimExtractor(_ScriptedCompletion(payload), as_of=AS_OF).extract(
        document_id="doc-cl",
        document_kind=DocumentKind.COVER_LETTER,
        normalised_text=LETTER,
    )

    assert result.claims
    assert all(c.self_authored for c in result.claims)
    assert all(c.source_span_ids for c in result.claims)


def test_self_authored_claims_never_satisfy_a_requirement() -> None:
    letter_claim = Claim(
        id="c-letter",
        competency="dbt",
        context="I have production dbt experience on Snowflake.",
        duration_signal="undated",
        recency_signal="undated",
        source_span_ids=("span-cl",),
        extraction_confidence=0.8,
        self_authored=True,
    )

    mappings = map_requirements((_req(),), (letter_claim,))

    assert len(mappings) == 1
    assert mappings[0].status is MappingStatus.MISSING


def test_a_cover_letter_does_not_change_the_fit_score() -> None:
    cv_claim = Claim(
        id="c-cv",
        competency="dbt",
        context="Owned dbt models in production on Snowflake.",
        duration_signal="2y",
        recency_signal="recent",
        source_span_ids=("span-cv",),
        extraction_confidence=0.9,
    )
    letter_claim = Claim(
        id="c-letter",
        competency="cuda",
        context="I led CUDA kernel work for the warehouse.",
        duration_signal="undated",
        recency_signal="undated",
        source_span_ids=("span-cl",),
        extraction_confidence=0.8,
        self_authored=True,
    )
    reqs = (_req(),)
    lean = map_requirements(reqs, (cv_claim,))
    padded = map_requirements(reqs, (cv_claim, letter_claim))

    assert lean == padded
    assert (
        score_fit(reqs, lean, (cv_claim,), RUBRIC).score
        == score_fit(reqs, padded, (cv_claim, letter_claim), RUBRIC).score
    )
