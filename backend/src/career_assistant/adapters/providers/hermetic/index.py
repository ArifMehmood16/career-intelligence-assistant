"""In-memory indexing adapters for deterministic test applications only."""

from __future__ import annotations

import math
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from career_assistant.application.ports.chunks import (
    ChunkProvenance,
    ChunkVector,
    EmbeddingModel,
    StoredChunk,
)
from career_assistant.application.ports.search import HybridQuery
from career_assistant.domain.chunking import Chunk
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.knowledge_graph import DocumentGraph
from career_assistant.domain.search import SearchHit, fuse, lexical_query_text


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


_WORD = re.compile(r"[a-z0-9]+")
_STOP_WORDS = frozenset(
    {"a", "an", "and", "for", "in", "of", "on", "or", "the", "to", "with"}
)


EVIDENCE_KINDS = frozenset({"experience", "project", "skills", "qualification"})


@dataclass(frozen=True, slots=True)
class ChunkSeed:
    text: str
    kind: str = "experience"
    context: str | None = None
    tech_terms: tuple[str, ...] = ()
    vector: tuple[float, ...] | None = None


@dataclass
class _Document:
    workspace_id: str
    kind: DocumentKind
    active: bool


@dataclass
class _Chunk:
    workspace_id: str
    document_id: str
    kind: str
    text: str
    context: str | None
    evidence_eligible: bool
    tech_terms: frozenset[str]
    vectors: dict[str, tuple[float, ...]] = field(default_factory=dict)


@dataclass
class InMemoryHybridSearch:
    documents: dict[str, _Document] = field(default_factory=dict)
    chunks: dict[str, _Chunk] = field(default_factory=dict)

    def add_document(
        self, document_id: str, workspace_id: str, kind: DocumentKind, *, active: bool
    ) -> None:
        self.documents[document_id] = _Document(workspace_id, kind, active)

    def add_chunk(self, chunk_id: str, document_id: str, seed: ChunkSeed) -> None:
        document = self.documents[document_id]
        self.chunks[chunk_id] = _Chunk(
            workspace_id=document.workspace_id,
            document_id=document_id,
            kind=seed.kind,
            text=seed.text,
            context=seed.context,
            evidence_eligible=seed.kind in EVIDENCE_KINDS,
            tech_terms=frozenset(t.casefold() for t in seed.tech_terms),
        )

    def add_vector(
        self, chunk_id: str, model_key: str, vector: tuple[float, ...]
    ) -> None:
        self.chunks[chunk_id].vectors[model_key] = vector

    def search(self, query: HybridQuery) -> tuple[SearchHit, ...]:
        eligible = {
            chunk_id: chunk
            for chunk_id, chunk in self.chunks.items()
            if self._eligible(chunk, query)
        }
        return fuse(
            dense=_dense(eligible, query)[: query.leg_count],
            lexical=_lexical(eligible, query)[: query.leg_count],
            exact=_exact(eligible, query)[: query.leg_count],
            weights=query.weights,
            rrf_k=query.rrf_k,
            limit=query.match_count,
        )

    def _eligible(self, chunk: _Chunk, query: HybridQuery) -> bool:
        document = self.documents[chunk.document_id]
        return (
            chunk.workspace_id == query.workspace_id
            and chunk.evidence_eligible
            and document.kind in query.sources
            and (document.kind is not DocumentKind.CV or document.active)
        )


def _dense(chunks: dict[str, _Chunk], query: HybridQuery) -> list[str]:
    scored = [
        (
            _cosine_distance(chunk.vectors[query.embedding_model_key], query.embedding),
            cid,
        )
        for cid, chunk in chunks.items()
        if query.embedding_model_key in chunk.vectors
    ]
    return [cid for _, cid in sorted(scored)]


def _lexical(chunks: dict[str, _Chunk], query: HybridQuery) -> list[str]:
    wanted = _words(lexical_query_text(query.text))
    scored = [
        (-len(wanted & _words(f"{chunk.context or ''} {chunk.text}")), cid)
        for cid, chunk in chunks.items()
        if chunk.kind != "contact"
    ]
    return [cid for score, cid in sorted(scored) if score < 0]


def _exact(chunks: dict[str, _Chunk], query: HybridQuery) -> list[str]:
    terms = set(query.terms)
    scored = [(-len(terms & chunk.tech_terms), cid) for cid, chunk in chunks.items()]
    return [cid for score, cid in sorted(scored) if score < 0]


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.casefold()) if w not in _STOP_WORDS}


def _cosine_distance(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    norm = math.hypot(*a) * math.hypot(*b)
    if norm == 0:
        return 1.0
    return 1.0 - sum(x * y for x, y in zip(a, b, strict=True)) / norm


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
