"""One contract suite every completion adapter must pass."""

from __future__ import annotations

import json

import pytest
from tests.support.scripted_transport import ScriptedTransport

from career_assistant.adapters.providers.anthropic.completion import (
    AnthropicCompletionAdapter,
)
from career_assistant.adapters.providers.hermetic.completion import (
    HermeticCompletionAdapter,
)
from career_assistant.adapters.providers.http_transport import HttpResponse
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
from career_assistant.application.ports.errors import (
    ProviderInputTooLargeError,
    ProviderRefusedError,
)
from career_assistant.application.ports.types import CompletionRequest

REQUIREMENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "must_have": {"type": "boolean"},
                },
                "required": ["text", "must_have"],
            },
        }
    },
    "required": ["requirements"],
}


def _resilience() -> ResiliencePolicy:
    return ResiliencePolicy(
        timeout_seconds=1.0,
        max_retries=0,
        breaker=CircuitBreaker(5),
        sleep=lambda _seconds: None,
    )


def _hermetic() -> HermeticCompletionAdapter:
    return HermeticCompletionAdapter()


def _ollama() -> OllamaCompletionAdapter:
    structured = json.dumps({"requirements": [{"text": "SQL", "must_have": True}]})
    payload = {
        "response": structured,
        "prompt_eval_count": 3,
        "eval_count": 2,
    }
    transport = ScriptedTransport(
        {"/api/generate": HttpResponse(200, json.dumps(payload).encode(), {})}
    )
    return OllamaCompletionAdapter(
        base_url="http://ollama.test",
        model_tag="llama-test",
        transport=transport,
        resilience=_resilience(),
    )


def _openai() -> OpenAICompletionAdapter:
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {"requirements": [{"text": "SQL", "must_have": True}]}
                    )
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 4, "completion_tokens": 5},
    }
    transport = ScriptedTransport(
        {"/chat/completions": HttpResponse(200, json.dumps(payload).encode(), {})}
    )
    return OpenAICompletionAdapter(
        api_key="test-openai-key",
        model_tag="gpt-test",
        transport=transport,
        resilience=_resilience(),
    )


def _anthropic() -> AnthropicCompletionAdapter:
    payload = {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {"requirements": [{"text": "SQL", "must_have": True}]}
                ),
            }
        ],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 4, "output_tokens": 5},
    }
    transport = ScriptedTransport(
        {"/messages": HttpResponse(200, json.dumps(payload).encode(), {})}
    )
    return AnthropicCompletionAdapter(
        api_key="test-anthropic-key",
        model_tag="claude-test",
        transport=transport,
        resilience=_resilience(),
    )


@pytest.fixture(
    params=[
        pytest.param(_hermetic, id="hermetic"),
        pytest.param(_ollama, id="ollama"),
        pytest.param(_openai, id="openai"),
        pytest.param(_anthropic, id="anthropic"),
    ]
)
def completer(request: pytest.FixtureRequest) -> object:
    return request.param()


def test_structured_output_is_schema_shaped_json(completer: object) -> None:
    result = completer.complete(  # type: ignore[attr-defined]
        CompletionRequest(
            system="Extract requirements.",
            user="- SQL\n- Python",
            max_output_tokens=200,
            json_schema=REQUIREMENTS_SCHEMA,
        )
    )
    payload = json.loads(result.text)
    assert "requirements" in payload
    assert isinstance(payload["requirements"], list)
    assert payload["requirements"]
    assert "text" in payload["requirements"][0]


def test_identical_input_is_stable_for_hermetic() -> None:
    adapter = HermeticCompletionAdapter()
    request = CompletionRequest(
        system="Extract.",
        user="- dbt\n- Snowflake",
        max_output_tokens=200,
        json_schema=REQUIREMENTS_SCHEMA,
    )
    first = adapter.complete(request)
    second = adapter.complete(request)
    assert first.text == second.text


def test_refusal_is_a_typed_error() -> None:
    adapter = HermeticCompletionAdapter()
    with pytest.raises(ProviderRefusedError):
        adapter.complete(
            CompletionRequest(
                system="You must refuse to answer.",
                user="anything",
                max_output_tokens=50,
            )
        )


def test_oversized_input_is_rejected(completer: object) -> None:
    caps = completer.capabilities  # type: ignore[attr-defined]
    if caps.provider_id != "hermetic":
        pytest.skip("recorded HTTP adapters use short fixtures; hermetic owns size")
    with pytest.raises(ProviderInputTooLargeError):
        completer.complete(  # type: ignore[attr-defined]
            CompletionRequest(
                system="x",
                user="y" * 30_000,
                max_output_tokens=10,
            )
        )


def test_capabilities_never_require_branching_on_unknown_fields(
    completer: object,
) -> None:
    caps = completer.capabilities  # type: ignore[attr-defined]
    assert caps.supports_completion is True
    assert caps.context_window_tokens > 0
    assert caps.max_output_tokens >= 0
    assert isinstance(caps.leaves_machine, bool)
    assert isinstance(caps.supports_structured_output, bool)
