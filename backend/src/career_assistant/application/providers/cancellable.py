"""Stop an analysis between provider calls once its job is cancelled.

Deleting a role or the CV cancels its analysis. The check runs before each call,
so no call starts after the job is cancelled. A call already in flight cannot be
interrupted from here: it finishes or times out, and the worker discards it.
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel

from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.structured import (
    StructuredCompletionPort,
    StructuredRequest,
    StructuredResult,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
)

# Raises JobCancelled when the job may not continue.
CancellationCheck = Callable[[], None]


class CancellableCompletion:
    def __init__(self, inner: CompletionPort, check: CancellationCheck) -> None:
        self._inner = inner
        self._check = check

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self._check()
        return self._inner.complete(request)


class CancellableStructured:
    def __init__(
        self, inner: StructuredCompletionPort, check: CancellationCheck
    ) -> None:
        self._inner = inner
        self._check = check

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete_structured[T: BaseModel](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]:
        self._check()
        return self._inner.complete_structured(request)


class CancellableEmbedding:
    def __init__(self, inner: EmbeddingPort, check: CancellationCheck) -> None:
        self._inner = inner
        self._check = check

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self._check()
        return self._inner.embed(request)
