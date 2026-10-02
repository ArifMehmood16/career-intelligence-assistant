"""DocumentIndexStore over PostgreSQL, one unit of work per call (PLAN 18.10)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ports.chunks import (
    ChunkProvenance,
    ChunkVector,
    EmbeddingModel,
    StoredChunk,
)
from career_assistant.domain.chunking import Chunk
from career_assistant.domain.knowledge_graph import DocumentGraph


class SqlDocumentIndexStore:
    def __init__(self, uow_factory: Callable[[], SqlUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def find_chunks(
        self, workspace_id: str, document_id: str, *, prompt_version: str
    ) -> tuple[StoredChunk, ...]:
        with self._uow_factory() as uow:
            return uow.chunks.find_chunks(
                workspace_id, document_id, prompt_version=prompt_version
            )

    def save_document(
        self,
        workspace_id: str,
        document_id: str,
        chunks: Sequence[Chunk],
        provenance: ChunkProvenance,
        graph: DocumentGraph,
    ) -> tuple[StoredChunk, ...]:
        with self._uow_factory() as uow:
            stored = uow.chunks.replace_chunks(
                workspace_id, document_id, chunks, provenance
            )
            uow.graph.replace_document_graph(workspace_id, document_id, graph)
            uow.commit()
        return stored

    def embedded_chunk_ids(
        self, workspace_id: str, document_id: str, model_key: str
    ) -> frozenset[str]:
        with self._uow_factory() as uow:
            return uow.chunks.embedded_chunk_ids(workspace_id, document_id, model_key)

    def save_vectors(
        self, workspace_id: str, model: EmbeddingModel, vectors: Sequence[ChunkVector]
    ) -> None:
        with self._uow_factory() as uow:
            uow.chunks.save_vectors(workspace_id, model, vectors)
            uow.commit()
