"""Log every model and embedding call: identity, sizes, timing, never text (ADR 017).

Decorators over the completion and embedding ports, applied by the provider
factory, so every caller is covered. A caller names the contract and attempt with
``llm_operation``; the pipeline task comes from the progress scope.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.progress import current_task
from career_assistant.application.ports.tool_calling import (
    ToolCallingPort,
    ToolCallingRequest,
    ToolCallingResult,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
)
from career_assistant.logconfig import log_event, log_failure

_log = logging.getLogger(__name__)
_operation: ContextVar[tuple[str, int] | None] = ContextVar(
    "llm_operation", default=None
)


@contextmanager
def llm_operation(contract: str, *, attempt: int) -> Iterator[None]:
    """Name the contract and attempt that calls inside the block serve."""
    token = _operation.set((contract, attempt))
    try:
        yield
    finally:
        _operation.reset(token)


def _call_fields(provider_id: str, model_tag: str) -> dict[str, object]:
    operation = _operation.get()
    contract, attempt = operation if operation else (None, None)
    return {
        "provider": provider_id,
        "model": model_tag,
        "contract": contract,
        "attempt": attempt,
        "task": current_task(),
    }


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


class LoggingCompletion:
    """Logs each call before it starts and after it replies or fails."""

    def __init__(
        self, inner: CompletionPort, *, provider_id: str, model_tag: str
    ) -> None:
        self._inner = inner
        self._provider_id = provider_id
        self._model_tag = model_tag

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete(self, request: CompletionRequest) -> CompletionResult:
        fields = _call_fields(self._provider_id, self._model_tag)
        log_event(
            _log,
            "Calling model",
            **fields,
            input_chars=len(request.system) + len(request.user),
            max_output_tokens=request.max_output_tokens,
            schema=request.json_schema is not None,
        )
        started = time.perf_counter()
        try:
            result = self._inner.complete(request)
        except Exception as error:
            log_failure(
                _log,
                "Model call failed",
                **fields,
                duration_ms=_elapsed_ms(started),
                error=type(error).__name__,
            )
            raise
        log_event(
            _log,
            "Model replied",
            **{**fields, "provider": result.provider_id, "model": result.model_tag},
            duration_ms=_elapsed_ms(started),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            reasoning_tokens=result.reasoning_tokens,
            finish_reason=result.finish_reason,
            output_chars=len(result.text),
            fallback_used=result.fallback_used or None,
        )
        return result


class LoggingEmbedding:
    """Logs each embedding call before it starts and after it replies or fails."""

    def __init__(
        self, inner: EmbeddingPort, *, provider_id: str, model_tag: str
    ) -> None:
        self._inner = inner
        self._provider_id = provider_id
        self._model_tag = model_tag

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        fields = _call_fields(self._provider_id, self._model_tag)
        log_event(
            _log,
            "Calling embedding model",
            **fields,
            inputs=len(request.texts),
            input_chars=sum(len(text) for text in request.texts),
            input_type=request.input_type,
        )
        started = time.perf_counter()
        try:
            result = self._inner.embed(request)
        except Exception as error:
            log_failure(
                _log,
                "Embedding call failed",
                **fields,
                duration_ms=_elapsed_ms(started),
                error=type(error).__name__,
            )
            raise
        log_event(
            _log,
            "Embedding model replied",
            **{**fields, "provider": result.provider_id, "model": result.model_tag},
            duration_ms=_elapsed_ms(started),
            vectors=len(result.vectors),
            dimensions=result.dimensions,
            input_tokens=result.input_tokens,
        )
        return result


class LoggingToolCaller:
    """Logs each tool-calling turn of the Ask agent before and after it runs."""

    def __init__(
        self, inner: ToolCallingPort, *, provider_id: str, model_tag: str
    ) -> None:
        self._inner = inner
        self._provider_id = provider_id
        self._model_tag = model_tag

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete(self, request: ToolCallingRequest) -> ToolCallingResult:
        fields = {
            **_call_fields(self._provider_id, self._model_tag),
            "contract": "tool-calling",
        }
        log_event(
            _log,
            "Calling model",
            **fields,
            messages=len(request.messages),
            tools_offered=len(request.tools),
            max_output_tokens=request.max_output_tokens,
        )
        started = time.perf_counter()
        try:
            result = self._inner.complete(request)
        except Exception as error:
            log_failure(
                _log,
                "Model call failed",
                **fields,
                duration_ms=_elapsed_ms(started),
                error=type(error).__name__,
            )
            raise
        log_event(
            _log,
            "Model replied",
            **{
                **fields,
                "provider": result.provider_id or self._provider_id,
                "model": result.model_tag or self._model_tag,
            },
            duration_ms=_elapsed_ms(started),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            tool_calls=len(result.tool_calls),
            output_chars=len(result.content),
        )
        return result
