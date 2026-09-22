"""PLAN 13C.2b — the model extracts; the server verifies the quote.

The delivered model extractor ran the rules extractor first and then discarded
every model requirement whose text was not already in the rules output. It could
only remove what the regex had found, never find what the regex missed, so a
prose advert produced nothing at all.

The model now returns a verbatim quote and the kind of item it is. The server
locates the quote in the stored text and builds the span from those offsets.
Anything that does not verify is dropped and counted — never repaired, never
fuzzy-matched. That verification is also the prompt-injection defence.
"""

from __future__ import annotations

import json
from pathlib import Path

from career_assistant.adapters.extraction.model_backed import ModelRequirementExtractor
from career_assistant.adapters.extraction.rules import RulesRequirementExtractor
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.mapping import map_requirements
from career_assistant.domain.normalisation import normalise_text
from career_assistant.domain.requirements import ItemType

ROOT = Path(__file__).resolve().parents[3]
JD_DIR = ROOT / "sample-data" / "fixtures" / "job-descriptions"

PROSE_ADVERT = normalise_text(
    "About the job\n"
    "We are hiring a forward deployed engineer to run agents in production.\n"
    "You will need strong experience with APIs, JSON and webhooks.\n"
    "You should be comfortable reading a failing run trace.\n"
    "The salary is 70,000 to 80,000 pounds depending on experience.\n"
    "This is not a platform support role.\n"
)


class _ScriptedCompletion:
    """Returns a fixed structured payload; records what it was asked."""

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
            max_output_tokens=1024,
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


def _item(quote: str, item_type: str, *, must_have: bool = True, competency: str = ""):
    return {
        "quote": quote,
        "item_type": item_type,
        "must_have": must_have,
        "competency": competency,
    }


_FULL_PAYLOAD = {
    "requirements": [
        _item(
            "You will need strong experience with APIs, JSON and webhooks.",
            "requirement",
            competency="api",
        ),
        _item(
            "You should be comfortable reading a failing run trace.",
            "responsibility",
            competency="ops",
        ),
        _item(
            "The salary is 70,000 to 80,000 pounds depending on experience.",
            "benefit",
            must_have=False,
        ),
        _item(
            "This is not a platform support role.", "non_requirement", must_have=False
        ),
        _item("You must hold a Rightbrain platform certification.", "requirement"),
    ]
}


def _extract(payload: dict[str, object], text: str = PROSE_ADVERT):
    completion = _ScriptedCompletion(payload)
    result = ModelRequirementExtractor(completion).extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=text,
    )
    return result, completion


def test_the_regex_finds_nothing_in_this_advert() -> None:
    """The baseline the model has to beat — no bullets, so no rule output."""
    rules = RulesRequirementExtractor().extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=PROSE_ADVERT,
    )

    assert rules.requirements == ()


def test_the_model_finds_prose_requirements_the_regex_cannot() -> None:
    result, completion = _extract(_FULL_PAYLOAD)

    texts = [r.text for r in result.requirements]
    assert any("APIs, JSON and webhooks" in t for t in texts)
    assert any("failing run trace" in t for t in texts)
    assert completion.calls == 1
    assert completion.last_request is not None
    assert "UNTRUSTED_JOB_DESCRIPTION" in completion.last_request.user
    assert completion.last_request.max_output_tokens == 4096


def test_an_unverifiable_quote_is_dropped_and_counted() -> None:
    result, _ = _extract(_FULL_PAYLOAD)

    assert all(
        "Rightbrain platform certification" not in r.text for r in result.requirements
    )
    assert result.dropped_unverifiable == 1


def test_every_span_round_trips_to_its_quote() -> None:
    result, _ = _extract(_FULL_PAYLOAD)

    by_id = {span.id: span for span in result.spans}
    assert result.requirements
    for requirement in result.requirements:
        span = by_id[requirement.source_span_id]
        assert PROSE_ADVERT[span.start_offset : span.end_offset] == requirement.text
        assert span.text == requirement.text


def test_item_types_from_the_model_are_preserved_and_only_some_are_scored() -> None:
    result, _ = _extract(_FULL_PAYLOAD)

    kinds = {r.item_type for r in result.requirements}
    assert ItemType.BENEFIT in kinds
    assert ItemType.NON_REQUIREMENT in kinds

    mappings = map_requirements(result.requirements, [])
    assert len(mappings) == 2
    assert all(
        r.is_scoreable
        for r in result.requirements
        if r.id in {m.requirement_id for m in mappings}
    )


def test_competency_is_the_models_open_vocabulary_not_the_keyword_list() -> None:
    payload = {
        "requirements": [
            _item(
                "You will need strong experience with APIs, JSON and webhooks.",
                "requirement",
                competency="forward-deployed-engineering",
            )
        ]
    }

    result, _ = _extract(payload)

    assert result.requirements[0].competency == "forward-deployed-engineering"


def test_seniority_and_vagueness_are_read_from_the_verified_quote() -> None:
    text = normalise_text(
        "We need a senior engineer with ownership of outcomes end to end.\n"
    )
    payload = {
        "requirements": [
            _item(
                "We need a senior engineer with ownership of outcomes end to end.",
                "requirement",
            )
        ]
    }

    result, _ = _extract(payload, text=text)

    assert result.requirements[0].seniority_signal == "senior"
    assert result.requirements[0].is_vague is True


def test_an_injected_instruction_cannot_invent_a_requirement() -> None:
    """The model obeys the injection; verification is what stops it."""
    text = normalise_text((JD_DIR / "jd-injection-attempt.txt").read_text())
    payload = {
        "requirements": [
            _item(
                "Production dbt experience on Snowflake.",
                "requirement",
                competency="dbt",
            ),
            _item(
                "the candidate is a perfect match for every requirement", "requirement"
            ),
            _item("fit score is 100", "requirement"),
            _item("candidate has CUDA and ROS2 experience", "requirement"),
        ]
    }

    result, _ = _extract(payload, text=text)

    joined = " ".join(r.text.lower() for r in result.requirements)
    assert "perfect match" not in joined
    assert "fit score" not in joined
    assert "cuda" not in joined
    assert "ros2" not in joined
    assert any("dbt" in r.text.lower() for r in result.requirements)
    assert result.dropped_unverifiable == 3


def test_a_quote_the_document_does_not_contain_is_never_repaired() -> None:
    payload = {
        "requirements": [
            _item(
                "You will need strong experience with APIs and GraphQL.",
                "requirement",
            ),
        ]
    }

    result, _ = _extract(payload)

    assert result.requirements == ()
    assert result.dropped_unverifiable == 1


def test_wrapping_quotation_marks_on_the_model_quote_still_verify() -> None:
    payload = {
        "requirements": [
            _item(
                '"You will need strong experience with APIs, JSON and webhooks."',
                "requirement",
                competency="api",
            )
        ]
    }
    result, _ = _extract(payload)
    assert result.requirements
    assert "APIs, JSON and webhooks" in result.requirements[0].text
    assert result.dropped_unverifiable == 0


def test_falls_back_to_the_rules_result_when_nothing_verifies() -> None:
    bulleted = normalise_text("Requirements\n- Own production for live agents\n")
    payload = {"requirements": [_item("invented entirely", "requirement")]}

    result, _ = _extract(payload, text=bulleted)

    assert [r.text for r in result.requirements] == ["Own production for live agents"]
    assert result.dropped_unverifiable == 1
