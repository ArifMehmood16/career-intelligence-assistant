"""Call accounting — identifiers and counts only, never content."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.progress import plan_calls, record_call
from career_assistant.application.ports.types import (
    CallRecord,
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
)


class CallAccountant:
    def __init__(self) -> None:
        self._records: list[CallRecord] = []
        self._lock = threading.Lock()

    def record(self, entry: CallRecord) -> None:
        with self._lock:
            self._records.append(entry)

    @property
    def records(self) -> tuple[CallRecord, ...]:
        with self._lock:
            return tuple(self._records)


class AccountingCompletion:
    """Records provider/model/token counts after each complete(), never the text."""

    def __init__(
        self,
        inner: CompletionPort,
        accountant: CallAccountant,
        *,
        workspace_id: str,
        purpose: str,
    ) -> None:
        self._inner = inner
        self._accountant = accountant
        self._workspace_id = workspace_id
        self._purpose = purpose

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete(self, request: CompletionRequest) -> CompletionResult:
        with accounting_operation("model"):
            result = self._inner.complete(request)
        self._accountant.record(
            CallRecord(
                provider_id=result.provider_id,
                model_tag=result.model_tag,
                operation="complete",
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                latency_ms=result.latency_ms,
                estimated_cost_usd=None,
                left_machine=result.left_machine,
                fallback_used=result.fallback_used,
                metadata={
                    "workspace_id": self._workspace_id,
                    "purpose": self._purpose,
                },
            )
        )
        return result


class AccountingEmbedding:
    """Records provider/model/token counts after each embed(), never the text."""

    def __init__(
        self,
        inner: EmbeddingPort,
        accountant: CallAccountant,
        *,
        workspace_id: str,
        purpose: str,
    ) -> None:
        self._inner = inner
        self._accountant = accountant
        self._workspace_id = workspace_id
        self._purpose = purpose

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        with accounting_operation("embedding"):
            result = self._inner.embed(request)
        self._accountant.record(
            CallRecord(
                provider_id=result.provider_id,
                model_tag=result.model_tag,
                operation="embed",
                input_tokens=result.input_tokens,
                output_tokens=None,
                latency_ms=result.latency_ms,
                estimated_cost_usd=None,
                left_machine=result.left_machine,
                metadata={
                    "workspace_id": self._workspace_id,
                    "purpose": self._purpose,
                    "vector_count": str(len(result.vectors)),
                },
            )
        )
        return result


@dataclass
class _Attempts:
    operation: str
    counted: int = 0


_attempts: ContextVar[_Attempts | None] = ContextVar("provider_attempts", default=None)


@contextmanager
def accounting_operation(operation: str) -> Iterator[None]:
    """Account for physical attempts, with one logical attempt for test adapters."""
    attempts = _Attempts(operation)
    token = _attempts.set(attempts)
    completed = False
    try:
        yield
        completed = True
    finally:
        _attempts.reset(token)
        if completed and attempts.counted == 0:
            record_call(operation)


@contextmanager
def provider_attempt(*, retry: bool = False) -> Iterator[None]:
    """Used inside resilience so a transport retry is also a counted request."""
    attempts = _attempts.get()
    if attempts is not None and retry:
        if attempts.operation == "model":
            plan_calls(model=1)
        else:
            plan_calls(embedding=1)
    try:
        yield
    finally:
        if attempts is not None:
            attempts.counted += 1
            record_call(attempts.operation)
