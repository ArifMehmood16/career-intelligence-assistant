"""Every model and embedding call is logged without its text (spec 013, FR-002)."""

from __future__ import annotations

import logging

import pytest
from tests.support.recording_progress import RecordingProgress
from tests.support.scripted_completion import Reply, ScriptedCompletion

from career_assistant.adapters.providers.factory import (
    build_completion_port,
    build_embedding_port,
)
from career_assistant.application.ports.errors import ProviderTransientError
from career_assistant.application.ports.progress import progress_scope
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
)
from career_assistant.application.providers.logging_ports import (
    LoggingCompletion,
    LoggingEmbedding,
    llm_operation,
)
from career_assistant.domain.progress import TaskKey
from career_assistant.settings import ProviderSettings

_PROMPT = "PRIVATE prompt about the candidate's Kubernetes work"
_REPLY = '{"verdicts": "PRIVATE reply text"}'
_REQUEST = CompletionRequest(system="system", user=_PROMPT, max_output_tokens=2_000)


def _events(caplog: pytest.LogCaptureFixture, name: str) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith(name)]


_CALLING = "Calling model "
_REPLIED = "Model replied "
_FAILED = "Model call failed "


def test_a_completion_logs_its_request_and_response_without_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    port = LoggingCompletion(
        ScriptedCompletion([Reply(_REPLY, input_tokens=900, output_tokens=120)]),
        provider_id="openai",
        model_tag="gpt-5-mini",
    )
    with caplog.at_level(logging.INFO):
        port.complete(_REQUEST)

    (request,) = _events(caplog, _CALLING)
    (response,) = _events(caplog, _REPLIED)
    assert request == (
        "Calling model provider=openai model=gpt-5-mini "
        f"input_chars={len('system') + len(_PROMPT)} "
        "max_output_tokens=2000 schema=False"
    )
    assert response.startswith("Model replied provider=scripted model=scripted-v1 ")
    assert "duration_ms=" in response
    assert "input_tokens=900 output_tokens=120 finish_reason=stop" in response
    assert f"output_chars={len(_REPLY)}" in response
    assert "PRIVATE" not in caplog.text


def test_reasoning_tokens_are_logged_when_the_vendor_reports_them(
    caplog: pytest.LogCaptureFixture,
) -> None:
    port = LoggingCompletion(
        ScriptedCompletion([Reply(_REPLY, output_tokens=400, reasoning_tokens=352)]),
        provider_id="openai",
        model_tag="gpt-5-mini",
    )
    with caplog.at_level(logging.INFO):
        port.complete(_REQUEST)

    (response,) = _events(caplog, _REPLIED)
    assert "output_tokens=400 reasoning_tokens=352 finish_reason=stop" in response


def test_the_operation_and_task_come_from_the_caller(
    caplog: pytest.LogCaptureFixture,
) -> None:
    port = LoggingCompletion(
        ScriptedCompletion([Reply(_REPLY)]), provider_id="openai", model_tag="m"
    )
    with (
        caplog.at_level(logging.INFO),
        progress_scope(RecordingProgress(), TaskKey.JUDGE),
        llm_operation("judge-v1", attempt=1),
    ):
        port.complete(_REQUEST)

    lines = _events(caplog, _CALLING) + _events(caplog, _REPLIED)
    assert len(lines) == 2
    for line in lines:
        assert "contract=judge-v1 attempt=1 task=judge" in line


class _Failing:
    @property
    def capabilities(self) -> CapabilityDescriptor:
        return ScriptedCompletion([]).capabilities

    def complete(self, request: CompletionRequest) -> CompletionResult:
        raise ProviderTransientError("PRIVATE vendor message")


def test_a_failed_call_logs_its_error_type_and_re_raises(
    caplog: pytest.LogCaptureFixture,
) -> None:
    port = LoggingCompletion(_Failing(), provider_id="openai", model_tag="m")
    with caplog.at_level(logging.INFO), pytest.raises(ProviderTransientError):
        port.complete(_REQUEST)

    (failed,) = _events(caplog, _FAILED)
    assert failed.startswith("Model call failed provider=openai model=m ")
    assert "error=ProviderTransientError" in failed
    assert "PRIVATE" not in caplog.text


class _Embedder:
    @property
    def capabilities(self) -> CapabilityDescriptor:
        return ScriptedCompletion([]).capabilities

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        return EmbeddingResult(
            vectors=tuple((0.1, 0.2, 0.3) for _ in request.texts),
            provider_id="openai",
            model_tag="text-embedding-3-small",
            dimensions=3,
            left_machine=True,
            input_tokens=42,
        )


def test_an_embedding_logs_counts_and_dimensions_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    port = LoggingEmbedding(
        _Embedder(), provider_id="openai", model_tag="text-embedding-3-small"
    )
    with caplog.at_level(logging.INFO):
        port.embed(
            EmbeddingRequest(texts=(_PROMPT, "PRIVATE two"), max_chars_per_text=1_000)
        )

    (request,) = _events(caplog, "Calling embedding model ")
    (response,) = _events(caplog, "Embedding model replied ")
    assert request.startswith(
        "Calling embedding model provider=openai model=text-embedding-3-small inputs=2"
    )
    assert f"input_chars={len(_PROMPT) + len('PRIVATE two')}" in request
    assert "vectors=2 dimensions=3 input_tokens=42" in response
    assert "PRIVATE" not in caplog.text


def test_the_provider_factory_returns_logging_ports(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = ProviderSettings(
        _env_file=None,  # type: ignore[call-arg]
        completion_provider="hermetic",
        embedding_provider="hermetic",
    )
    completion = build_completion_port(settings)
    embedding = build_embedding_port(settings)
    with caplog.at_level(logging.INFO):
        completion.complete(_REQUEST)
        embedding.embed(EmbeddingRequest(texts=("one",), max_chars_per_text=100))

    (model,) = _events(caplog, _CALLING)
    (embedder,) = _events(caplog, "Calling embedding model ")
    assert model.startswith("Calling model provider=hermetic model=rules-v1 ")
    assert embedder.startswith(
        "Calling embedding model provider=hermetic model=lexical-hash-v1 "
    )
