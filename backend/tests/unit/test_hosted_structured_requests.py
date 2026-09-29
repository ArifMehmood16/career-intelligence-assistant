"""Hosted adapters enforce the schema through the API, not the prompt (PLAN 18.1)."""

from __future__ import annotations

import json

from tests.support.recording_transport import RecordingTransport

from career_assistant.adapters.providers.anthropic.completion import (
    AnthropicCompletionAdapter,
)
from career_assistant.adapters.providers.openai.completion import (
    OpenAICompletionAdapter,
)
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
)
from career_assistant.adapters.providers.schema_dialects import (
    anthropic_output_schema,
    openai_strict_schema,
)
from career_assistant.application.ports.types import CompletionRequest, ModelProfile

_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 4},
        "note": {"type": "string"},
    },
    "required": ["score"],
}


def _resilience() -> ResiliencePolicy:
    return ResiliencePolicy(
        timeout_seconds=1.0,
        max_retries=0,
        breaker=CircuitBreaker(5),
        sleep=lambda _seconds: None,
    )


def _profile(*, sampling: bool) -> ModelProfile:
    return ModelProfile(
        context_window_tokens=128_000,
        max_output_tokens=16_384,
        supports_temperature=sampling,
        supports_seed=sampling,
    )


def _request(**overrides: object) -> CompletionRequest:
    values: dict[str, object] = {
        "system": "Judge.",
        "user": "untrusted text",
        "max_output_tokens": 900,
        "json_schema": _SCHEMA,
    }
    values.update(overrides)
    return CompletionRequest(**values)  # type: ignore[arg-type]


def _openai_reply(finish_reason: str = "stop") -> dict[str, object]:
    return {
        "choices": [
            {"message": {"content": '{"score": 3}'}, "finish_reason": finish_reason}
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 4},
    }


def _openai(
    transport: RecordingTransport, *, sampling: bool = True
) -> OpenAICompletionAdapter:
    return OpenAICompletionAdapter(
        api_key="test-key",
        model_tag="gpt-test",
        transport=transport,
        resilience=_resilience(),
        profile=_profile(sampling=sampling),
    )


def _anthropic_reply(stop_reason: str = "end_turn") -> dict[str, object]:
    return {
        "content": [{"type": "text", "text": '{"score": 3}'}],
        "stop_reason": stop_reason,
        "usage": {"input_tokens": 5, "output_tokens": 4},
    }


def _anthropic(
    transport: RecordingTransport, *, sampling: bool = True
) -> AnthropicCompletionAdapter:
    return AnthropicCompletionAdapter(
        api_key="test-key",
        model_tag="claude-test",
        transport=transport,
        resilience=_resilience(),
        profile=_profile(sampling=sampling),
    )


def test_openai_sends_the_strict_dialect_of_the_schema() -> None:
    transport = RecordingTransport(_openai_reply())

    _openai(transport).complete(_request())

    response_format = transport.last.body["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"] == openai_strict_schema(_SCHEMA)


def test_openai_uses_max_completion_tokens() -> None:
    transport = RecordingTransport(_openai_reply())

    _openai(transport).complete(_request())

    assert transport.last.body["max_completion_tokens"] == 900
    assert "max_tokens" not in transport.last.body


def test_openai_sampling_settings_follow_the_profile() -> None:
    accepted = RecordingTransport(_openai_reply())
    _openai(accepted).complete(_request(temperature=0.0, seed=7))
    refused = RecordingTransport(_openai_reply())
    _openai(refused, sampling=False).complete(_request(temperature=0.0, seed=7))

    assert accepted.last.body["temperature"] == 0.0
    assert accepted.last.body["seed"] == 7
    assert "temperature" not in refused.last.body
    assert "seed" not in refused.last.body


def test_anthropic_sends_the_schema_as_output_config_not_as_prompt_text() -> None:
    transport = RecordingTransport(_anthropic_reply())

    _anthropic(transport).complete(_request())

    body = transport.last.body
    assert body["output_config"] == {
        "format": {"type": "json_schema", "schema": anthropic_output_schema(_SCHEMA)}
    }
    assert body["messages"] == [{"role": "user", "content": "untrusted text"}]


def test_anthropic_reports_a_max_tokens_stop_as_truncation() -> None:
    finished = _anthropic(RecordingTransport(_anthropic_reply())).complete(_request())
    cut = _anthropic(RecordingTransport(_anthropic_reply("max_tokens"))).complete(
        _request()
    )

    assert finished.finish_reason == "stop"
    assert cut.finish_reason == "length"


def test_anthropic_sends_temperature_only_when_the_model_accepts_it() -> None:
    accepted = RecordingTransport(_anthropic_reply())
    _anthropic(accepted).complete(_request(temperature=0.0, seed=7))
    refused = RecordingTransport(_anthropic_reply())
    _anthropic(refused, sampling=False).complete(_request(temperature=0.0))

    assert accepted.last.body["temperature"] == 0.0
    assert "seed" not in accepted.last.body
    assert "temperature" not in refused.last.body


def test_openai_hides_the_nulls_strict_mode_forces_into_optional_fields() -> None:
    reply = _openai_reply()
    reply["choices"][0]["message"]["content"] = '{"score": 3, "note": null}'  # type: ignore[index]

    result = _openai(RecordingTransport(reply)).complete(_request())

    assert json.loads(result.text) == {"score": 3}
