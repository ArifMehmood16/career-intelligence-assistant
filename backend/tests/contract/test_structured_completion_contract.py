"""A structured completion works through every HTTP completion adapter (PLAN 18.2).

Recorded replies only; no network. Each adapter is built the way the catalogue
would build it for a model with native structured output, so the OpenAI reply
arrives in strict mode with nulls in optional fields.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from tests.support.recording_transport import RecordingTransport

from career_assistant.adapters.providers.anthropic.completion import (
    AnthropicCompletionAdapter,
)
from career_assistant.adapters.providers.ollama.completion import (
    OllamaCompletionAdapter,
)
from career_assistant.adapters.providers.openai.completion import (
    OpenAICompletionAdapter,
)
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
)
from career_assistant.application.contracts.agent import AgentAnswer
from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.structured import StructuredRequest
from career_assistant.application.ports.types import ModelProfile
from career_assistant.application.providers.structured import StructuredCompleter

_ANSWER = {"answer": "Northwind is the strongest evidence.", "support": "grounded"}
# What OpenAI strict mode sends back: optional properties present as null.
_STRICT_ANSWER = {**_ANSWER, "citations": None}
_PROFILE = ModelProfile(
    context_window_tokens=32_768, max_output_tokens=4_096, native_structured_output=True
)


def _resilience() -> ResiliencePolicy:
    return ResiliencePolicy(
        timeout_seconds=1.0,
        max_retries=0,
        breaker=CircuitBreaker(5),
        sleep=lambda _seconds: None,
    )


def _ollama() -> CompletionPort:
    reply = {"message": {"content": json.dumps(_ANSWER)}, "done_reason": "stop"}
    return OllamaCompletionAdapter(
        base_url="http://ollama.test",
        model_tag="m",
        transport=RecordingTransport(reply),
        resilience=_resilience(),
        profile=_PROFILE,
    )


def _openai() -> CompletionPort:
    reply = {
        "choices": [
            {
                "message": {"content": json.dumps(_STRICT_ANSWER)},
                "finish_reason": "stop",
            }
        ]
    }
    return OpenAICompletionAdapter(
        api_key="k",
        model_tag="m",
        transport=RecordingTransport(reply),
        resilience=_resilience(),
        profile=_PROFILE,
    )


def _anthropic() -> CompletionPort:
    reply = {
        "content": [{"type": "text", "text": json.dumps(_ANSWER)}],
        "stop_reason": "end_turn",
    }
    return AnthropicCompletionAdapter(
        api_key="k",
        model_tag="m",
        transport=RecordingTransport(reply),
        resilience=_resilience(),
        profile=_PROFILE,
    )


@pytest.mark.parametrize(
    "build",
    [_ollama, _openai, _anthropic],
    ids=["ollama", "openai", "anthropic"],
)
def test_each_adapter_yields_a_validated_contract_object(
    build: Callable[[], CompletionPort],
) -> None:
    result = StructuredCompleter(build()).complete_structured(
        StructuredRequest(
            contract=AgentAnswer,
            system="Answer from the evidence.",
            user="question",
            max_output_tokens=500,
        )
    )

    assert result.value == AgentAnswer.model_validate(_ANSWER)
    assert result.attempts == 1
