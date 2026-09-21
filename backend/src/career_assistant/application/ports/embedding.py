"""Embedding port — vectors for mapping candidates."""

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


class EmbeddingCachePort(Protocol):
    """Read and write vectors by owner, provider, model and text hash."""

    def get(
        self,
        workspace_id: str,
        *,
        owner_kind: str,
        owner_id: str,
        provider: str,
        model_tag: str,
        text_sha256: str,
    ) -> tuple[float, ...] | None: ...

    def put(
        self,
        workspace_id: str,
        *,
        owner_kind: str,
        owner_id: str,
        provider: str,
        model_tag: str,
        text_sha256: str,
        dimensions: int,
        vector: tuple[float, ...],
    ) -> None: ...
