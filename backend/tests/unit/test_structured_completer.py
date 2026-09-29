"""A structured completion returns a validated contract object (PLAN 18.2).

One repair call is allowed. A reply that is still invalid, or a reply cut by the
output limit, is a typed failure the caller turns into an incomplete analysis — it
never becomes a partial result.
"""

from __future__ import annotations

import json

import pytest
from tests.support.scripted_completion import Reply, ScriptedCompletion

from career_assistant.application.contracts.agent import AgentAnswer
from career_assistant.application.ports.errors import (
    StructuredOutputInvalidError,
    StructuredOutputTruncatedError,
)
from career_assistant.application.ports.structured import StructuredRequest
from career_assistant.application.providers.structured import StructuredCompleter

_VALID = json.dumps(
    {"answer": "Northwind is your strongest evidence.", "support": "grounded"}
)
_INVALID = json.dumps({"answer": "Northwind.", "support": "certain"})


def _request() -> StructuredRequest[AgentAnswer]:
    return StructuredRequest(
        contract=AgentAnswer,
        system="Answer from the evidence.",
        user="UNTRUSTED question",
        max_output_tokens=800,
        temperature=0.0,
        seed=7,
    )


def test_a_valid_reply_returns_the_parsed_contract() -> None:
    port = ScriptedCompletion([Reply(_VALID)])

    result = StructuredCompleter(port).complete_structured(_request())

    assert isinstance(result.value, AgentAnswer)
    assert result.value.support == "grounded"
    assert result.attempts == 1
    assert result.provider_id == "scripted"
    assert result.model_tag == "scripted-v1"


def test_the_request_carries_the_contract_schema_and_sampling_settings() -> None:
    port = ScriptedCompletion([Reply(_VALID)])

    StructuredCompleter(port).complete_structured(_request())

    sent = port.requests[0]
    assert sent.json_schema == AgentAnswer.model_json_schema()
    assert sent.temperature == 0.0
    assert sent.seed == 7
    assert sent.max_output_tokens == 800


def test_an_invalid_reply_gets_one_repair_call_listing_the_errors() -> None:
    port = ScriptedCompletion([Reply(_INVALID), Reply(_VALID)])

    result = StructuredCompleter(port).complete_structured(_request())

    assert result.attempts == 2
    repair = port.requests[1].user
    assert repair.startswith("UNTRUSTED question")
    assert f"<previous_response>\n{_INVALID}\n</previous_response>" in repair
    assert "- support: Input should be" in repair


def test_tokens_are_summed_across_attempts() -> None:
    port = ScriptedCompletion(
        [
            Reply(_INVALID, input_tokens=100, output_tokens=20),
            Reply(_VALID, input_tokens=130, output_tokens=25),
        ]
    )

    result = StructuredCompleter(port).complete_structured(_request())

    assert result.input_tokens == 230
    assert result.output_tokens == 45


def test_a_reply_still_invalid_after_the_repair_is_a_typed_failure() -> None:
    port = ScriptedCompletion([Reply(_INVALID), Reply("not json at all")])

    with pytest.raises(StructuredOutputInvalidError) as caught:
        StructuredCompleter(port).complete_structured(_request())

    assert caught.value.contract_version == AgentAnswer.contract_version
    assert caught.value.error_count >= 1
    assert "Northwind" not in str(caught.value)
    assert len(port.requests) == 2


def test_a_truncated_reply_fails_without_a_repair_call() -> None:
    port = ScriptedCompletion([Reply('{"answer": "North', finish_reason="length")])

    with pytest.raises(StructuredOutputTruncatedError):
        StructuredCompleter(port).complete_structured(_request())

    assert len(port.requests) == 1


def test_without_structured_output_the_schema_goes_in_the_system_prompt() -> None:
    port = ScriptedCompletion([Reply(_VALID)], structured_output=False)

    StructuredCompleter(port).complete_structured(_request())

    sent = port.requests[0]
    assert sent.json_schema is None
    assert json.dumps(AgentAnswer.model_json_schema()) in sent.system
