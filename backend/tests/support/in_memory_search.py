"""An in-memory HybridSearchPort for tests. Passes the same contract suite as SQL.

Its lexical leg is word overlap after dropping a few stop words, not PostgreSQL's
stemmer, so stemming and parser behaviour are pinned by the SQL-only tests.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from career_assistant.application.ports.search import HybridQuery
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.search import SearchHit, fuse, lexical_query_text

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
