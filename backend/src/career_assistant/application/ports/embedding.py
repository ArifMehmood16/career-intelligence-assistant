"""Embedding port — vectors for retrieval and mapping candidates."""

from __future__ import annotations

from typing import Protocol

from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    EmbeddingRequest,
    EmbeddingResult,
)


class EmbeddingPort(Protocol):
    @property
    def capabilities(self) -> CapabilityDescriptor: ...

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...
