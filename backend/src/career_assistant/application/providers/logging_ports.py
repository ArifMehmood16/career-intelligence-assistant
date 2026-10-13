"""Log every model and embedding call: identity, sizes, timing, never text (ADR 017).

Decorators over the completion and embedding ports, applied by the provider
factory, so every caller is covered. The caller names the operation (for example
a contract and its attempt) with ``llm_operation``; the pipeline task comes from
the progress scope.
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
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
)
from career_assistant.logconfig import log_event, log_failure

_log = logging.getLogger(__name__)
_operation: ContextVar[str | None] = ContextVar("llm_operation", default=None)


@contextmanager
def llm_operation(name: str) -> Iterator[None]:
    """Name the calls made inside the block, e.g. ``judge-v1#2``."""
    token = _operation.set(name)
    try:
        yield
    finally:
        _operation.reset(token)


def _call_fields(provider_id: str, model_tag: str, default: str) -> dict[str, object]:
    return {
        "provider": provider_id,
        "model": model_tag,
        "operation": _operation.get() or default,
        "task": current_task(),
    }


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


class LoggingCompletion:
    """Logs llm.request before and llm.response or llm.failed after each call."""

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
        fields = _call_fields(self._provider_id, self._model_tag, "completion")
        log_event(
            _log,
            "llm.request",
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
                "llm.failed",
                **fields,
                duration_ms=_elapsed_ms(started),
                error=type(error).__name__,
            )
            raise
        log_event(
            _log,
            "llm.response",
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
    """Logs llm.request before and llm.response or llm.failed after each embed."""

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
        fields = _call_fields(self._provider_id, self._model_tag, "embedding")
        log_event(
            _log,
            "llm.request",
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
                "llm.failed",
                **fields,
                duration_ms=_elapsed_ms(started),
                error=type(error).__name__,
            )
            raise
        log_event(
            _log,
            "llm.response",
            **{**fields, "provider": result.provider_id, "model": result.model_tag},
            duration_ms=_elapsed_ms(started),
            vectors=len(result.vectors),
            dimensions=result.dimensions,
            input_tokens=result.input_tokens,
        )
        return result
