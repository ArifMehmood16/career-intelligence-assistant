"""In-memory DocumentIndexStore for application tests (PLAN 18.10)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

from career_assistant.application.ports.chunks import (
    ChunkProvenance,
    ChunkVector,
    EmbeddingModel,
    StoredChunk,
)
from career_assistant.domain.chunking import Chunk
from career_assistant.domain.knowledge_graph import DocumentGraph


@dataclass
class InMemoryIndexStore:
    chunks: dict[str, tuple[StoredChunk, ...]] = field(default_factory=dict)
    provenance: dict[str, ChunkProvenance] = field(default_factory=dict)
    graphs: dict[str, DocumentGraph] = field(default_factory=dict)
    vectors: dict[tuple[str, str], tuple[float, ...]] = field(default_factory=dict)

    def find_chunks(
        self, workspace_id: str, document_id: str, *, prompt_version: str
    ) -> tuple[StoredChunk, ...]:
        kept = self.provenance.get(document_id)
        if kept is None or kept.prompt_version != prompt_version:
            return ()
        return self.chunks[document_id]

    def save_document(
        self,
        workspace_id: str,
        document_id: str,
        chunks: Sequence[Chunk],
        provenance: ChunkProvenance,
        graph: DocumentGraph,
    ) -> tuple[StoredChunk, ...]:
        stored = tuple(
            StoredChunk(str(uuid.uuid4()), document_id, chunk) for chunk in chunks
        )
        self.chunks[document_id] = stored
        self.provenance[document_id] = provenance
        self.graphs[document_id] = graph
        return stored

    def embedded_chunk_ids(
        self, workspace_id: str, document_id: str, model_key: str
    ) -> frozenset[str]:
        ids = {s.chunk_id for s in self.chunks.get(document_id, ())}
        return frozenset(cid for cid, key in self.vectors if key == model_key) & ids

    def save_vectors(
        self, workspace_id: str, model: EmbeddingModel, vectors: Sequence[ChunkVector]
    ) -> None:
        for item in vectors:
            self.vectors[(item.chunk_id, model.key)] = item.vector
