"""Stored chunks and their vectors (ADR 013, PLAN 18.10)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from career_assistant.application.ports.types import EmbeddingInputType
from career_assistant.domain.chunking import Chunk
from career_assistant.domain.knowledge_graph import DocumentGraph


@dataclass(frozen=True, slots=True)
class ChunkProvenance:
    provider_id: str
    model_tag: str
    prompt_version: str


@dataclass(frozen=True, slots=True)
class StoredChunk:
    chunk_id: str
    document_id: str
    chunk: Chunk


@dataclass(frozen=True, slots=True)
class EmbeddingModel:
    provider_id: str
    model_tag: str
    dimensions: int
    input_type: EmbeddingInputType

    @property
    def key(self) -> str:
        """Changing any part re-embeds; hybrid_search matches on it exactly."""
        return (
            f"{self.provider_id}:{self.model_tag}:{self.dimensions}:{self.input_type}"
        )


@dataclass(frozen=True, slots=True)
class ChunkVector:
    chunk_id: str
    vector: tuple[float, ...]


class DocumentIndexStore(Protocol):
    """One transaction per call, so no model call runs inside a transaction."""

    def find_chunks(
        self, workspace_id: str, document_id: str, *, prompt_version: str
    ) -> tuple[StoredChunk, ...]: ...

    def save_document(
        self,
        workspace_id: str,
        document_id: str,
        chunks: Sequence[Chunk],
        provenance: ChunkProvenance,
        graph: DocumentGraph,
    ) -> tuple[StoredChunk, ...]: ...

    def embedded_chunk_ids(
        self, workspace_id: str, document_id: str, model_key: str
    ) -> frozenset[str]: ...

    def save_vectors(
        self, workspace_id: str, model: EmbeddingModel, vectors: Sequence[ChunkVector]
    ) -> None: ...


class ChunkRepository(Protocol):
    def find_chunks(
        self, workspace_id: str, document_id: str, *, prompt_version: str
    ) -> tuple[StoredChunk, ...]: ...

    def replace_chunks(
        self,
        workspace_id: str,
        document_id: str,
        chunks: Sequence[Chunk],
        provenance: ChunkProvenance,
    ) -> tuple[StoredChunk, ...]: ...

    def load_chunks(
        self, workspace_id: str, chunk_ids: Sequence[str]
    ) -> tuple[StoredChunk, ...]: ...

    def embedded_chunk_ids(
        self, workspace_id: str, document_id: str, model_key: str
    ) -> frozenset[str]: ...

    def save_vectors(
        self, workspace_id: str, model: EmbeddingModel, vectors: Sequence[ChunkVector]
    ) -> None: ...
