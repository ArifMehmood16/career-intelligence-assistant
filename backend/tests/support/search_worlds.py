"""Seed chunks for a HybridSearchPort under test, in memory or in PostgreSQL."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Protocol

from tests.support.in_memory_search import (
    EVIDENCE_KINDS,
    ChunkSeed,
    InMemoryHybridSearch,
)

from career_assistant.application.ports.search import HybridSearchPort
from career_assistant.domain.documents import DocumentKind

MODEL_KEY = "test:embed-v1:3:document"
__all__ = ["EVIDENCE_KINDS", "MODEL_KEY", "ChunkSeed", "InMemoryWorld", "SearchWorld"]


class SearchWorld(Protocol):
    @property
    def search(self) -> HybridSearchPort: ...

    def workspace(self) -> str: ...

    def document(
        self, workspace_id: str, kind: DocumentKind, *, active: bool
    ) -> str: ...

    def chunk(self, document_id: str, seed: ChunkSeed) -> str: ...


@dataclass
class InMemoryWorld:
    port: InMemoryHybridSearch = field(default_factory=InMemoryHybridSearch)

    @property
    def search(self) -> HybridSearchPort:
        return self.port

    def workspace(self) -> str:
        return str(uuid.uuid4())

    def document(self, workspace_id: str, kind: DocumentKind, *, active: bool) -> str:
        document_id = str(uuid.uuid4())
        self.port.add_document(document_id, workspace_id, kind, active=active)
        return document_id

    def chunk(self, document_id: str, seed: ChunkSeed) -> str:
        chunk_id = str(uuid.uuid4())
        self.port.add_chunk(chunk_id, document_id, seed)
        if seed.vector is not None:
            self.port.add_vector(chunk_id, MODEL_KEY, seed.vector)
        return chunk_id
