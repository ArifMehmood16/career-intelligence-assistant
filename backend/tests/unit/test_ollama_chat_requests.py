"""The Ollama adapter uses the chat API with an explicit context window (PLAN 18.1).

Without `num_ctx` the prompt window is the Ollama server's default, not the one the
capability descriptor reports, and a long prompt is cut without an error.
"""

from __future__ import annotations

from tests.support.recording_transport import RecordingTransport

from career_assistant.adapters.providers.ollama.completion import (
    OllamaCompletionAdapter,
)
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
)
from career_assistant.application.ports.types import CompletionRequest, ModelProfile

_SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}}


def _adapter(
    transport: RecordingTransport, *, temperature: bool = True
) -> OllamaCompletionAdapter:
    return OllamaCompletionAdapter(
        base_url="http://ollama.test",
        model_tag="qwen-test",
        transport=transport,
        resilience=ResiliencePolicy(
            timeout_seconds=1.0,
            max_retries=0,
            breaker=CircuitBreaker(5),
            sleep=lambda _seconds: None,
        ),
        profile=ModelProfile(
            context_window_tokens=32_768,
            max_output_tokens=8_192,
            supports_temperature=temperature,
            supports_seed=temperature,
        ),
    )


def _chat(content: str, done_reason: str = "stop") -> dict[str, object]:
    return {
        "message": {"role": "assistant", "content": content},
        "done_reason": done_reason,
        "prompt_eval_count": 11,
        "eval_count": 7,
    }


def _request(**overrides: object) -> CompletionRequest:
    values: dict[str, object] = {
        "system": "Classify.",
        "user": "untrusted text",
        "max_output_tokens": 500,
        "json_schema": _SCHEMA,
    }
    values.update(overrides)
    return CompletionRequest(**values)  # type: ignore[arg-type]


def test_it_posts_system_and_user_messages_to_the_chat_api() -> None:
    transport = RecordingTransport(_chat('{"ok": true}'))

    _adapter(transport).complete(_request())

    assert transport.last.url.endswith("/api/chat")
    assert transport.last.body["messages"] == [
        {"role": "system", "content": "Classify."},
        {"role": "user", "content": "untrusted text"},
    ]
    assert transport.last.body["format"] == _SCHEMA


def test_it_sets_the_context_window_from_the_profile() -> None:
    transport = RecordingTransport(_chat("{}"))

    _adapter(transport).complete(_request())

    options = transport.last.body["options"]
    assert options["num_ctx"] == 32_768
    assert options["num_predict"] == 500


def test_the_reply_text_and_token_counts_come_from_the_chat_message() -> None:
    result = _adapter(RecordingTransport(_chat('{"ok": true}'))).complete(_request())

    assert result.text == '{"ok": true}'
    assert result.input_tokens == 11
    assert result.output_tokens == 7
    assert result.finish_reason == "stop"


def test_a_length_stop_is_reported_as_truncation() -> None:
    result = _adapter(RecordingTransport(_chat('{"ok": tr', "length"))).complete(
        _request()
    )

    assert result.finish_reason == "length"


def test_temperature_and_seed_are_sent_when_the_model_accepts_them() -> None:
    transport = RecordingTransport(_chat("{}"))

    _adapter(transport).complete(_request(temperature=0.0, seed=7))

    assert transport.last.body["options"]["temperature"] == 0.0
    assert transport.last.body["options"]["seed"] == 7


def test_temperature_and_seed_are_left_out_when_the_model_does_not_accept_them() -> (
    None
):
    transport = RecordingTransport(_chat("{}"))

    _adapter(transport, temperature=False).complete(_request(temperature=0.0, seed=7))

    assert "temperature" not in transport.last.body["options"]
    assert "seed" not in transport.last.body["options"]
