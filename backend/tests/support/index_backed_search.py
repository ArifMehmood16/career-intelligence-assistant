"""A HybridSearchPort over whatever an InMemoryIndexStore holds (PLAN 18.10)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from tests.support.in_memory_index import InMemoryIndexStore
from tests.support.in_memory_search import ChunkSeed, InMemoryHybridSearch

from career_assistant.application.ports.search import HybridQuery
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.search import SearchHit


@dataclass
class IndexBackedSearch:
    store: InMemoryIndexStore
    workspace_id: str
    kinds: Mapping[str, DocumentKind]

    def search(self, query: HybridQuery) -> tuple[SearchHit, ...]:
        index = InMemoryHybridSearch()
        for document_id, stored in self.store.chunks.items():
            index.add_document(
                document_id, self.workspace_id, self.kinds[document_id], active=True
            )
            for s in stored:
                index.add_chunk(
                    s.chunk_id,
                    document_id,
                    ChunkSeed(
                        text=s.chunk.text,
                        kind=s.chunk.kind,
                        context=s.chunk.context,
                        tech_terms=tuple(t.surface for t in s.chunk.tech_terms),
                    ),
                )
        for (chunk_id, model_key), vector in self.store.vectors.items():
            index.add_vector(chunk_id, model_key, vector)
        return index.search(query)
