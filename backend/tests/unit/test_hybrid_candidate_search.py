"""PLAN 18.10 — the judge's candidates come from hybrid search over the CV."""

from __future__ import annotations

import uuid
from datetime import date

from tests.support.in_memory_search import ChunkSeed, InMemoryHybridSearch
from tests.support.v2_chunks import cv_chunks

from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.application.judge.candidate_search import HybridCandidateSearch
from career_assistant.application.ports.chunks import StoredChunk
from career_assistant.application.ports.search import HybridQuery
from career_assistant.application.ports.types import EmbeddingRequest, EmbeddingResult
from career_assistant.domain.chunking import retrieval_text
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.judging import RequirementPacket
from career_assistant.domain.recency import DateRange
from career_assistant.domain.search import SearchHit

WS = "ws-1"
DOCUMENT_KEY = "hermetic:lexical-hash-v1:64:document"
REQUIREMENT = RequirementPacket(
    requirement_id="req-1",
    quote="5+ years of Python and Postgres",
    statement="5+ years of Python",
    must_have=True,
    terms=("Python",),
    candidates=(),
)


class RecordingSearch:
    def __init__(self, inner: InMemoryHybridSearch) -> None:
        self._inner = inner
        self.queries: list[HybridQuery] = []

    def search(self, query: HybridQuery) -> tuple[SearchHit, ...]:
        self.queries.append(query)
        return self._inner.search(query)


class RecordingEmbedding(HermeticEmbeddingAdapter):
    def __init__(self) -> None:
        self.requests: list[EmbeddingRequest] = []

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.requests.append(request)
        return super().embed(request)


def _world() -> tuple[
    HybridCandidateSearch, RecordingSearch, RecordingEmbedding, tuple[StoredChunk, ...]
]:
    stored = tuple(StoredChunk(str(uuid.uuid4()), "cv", c) for c in cv_chunks())
    index = InMemoryHybridSearch()
    index.add_document("cv", WS, DocumentKind.CV, active=True)
    embedder = HermeticEmbeddingAdapter()
    for s in stored:
        index.add_chunk(
            s.chunk_id,
            "cv",
            ChunkSeed(
                text=s.chunk.text,
                kind=s.chunk.kind,
                context=s.chunk.context,
                tech_terms=tuple(t.surface for t in s.chunk.tech_terms),
            ),
        )
        text = retrieval_text(s.chunk)
        if s.chunk.evidence_eligible and text:
            vector = embedder.embed(EmbeddingRequest((text,), 8_000)).vectors[0]
            index.add_vector(s.chunk_id, DOCUMENT_KEY, vector)
    search = RecordingSearch(index)
    embedding = RecordingEmbedding()
    finder = HybridCandidateSearch(
        workspace_id=WS,
        cv_chunks=stored,
        embedding=embedding,
        search=search,
        max_chars_per_text=8_000,
    )
    return finder, search, embedding, stored


def test_candidates_carry_the_chunk_text_role_and_dates() -> None:
    finder, _, _, stored = _world()

    found = finder.find(REQUIREMENT, REQUIREMENT.statement)

    experience = next(c for c in found.candidates if c.kind == "experience")
    assert experience.chunk_id == stored[1].chunk_id
    assert experience.text == "Built retrieval over Postgres and Python."
    assert experience.source == "cv"
    assert experience.role == "Senior Data Engineer at Northwind"
    assert experience.dates == DateRange(date(2021, 3, 1), date(2024, 12, 1))
    assert [h.chunk_id for h in found.hits] == [c.chunk_id for c in found.candidates]


def test_the_query_is_embedded_as_a_query_and_matched_to_document_vectors() -> None:
    finder, search, embedding, _ = _world()

    finder.find(REQUIREMENT, "Python data platform")

    assert [r.input_type for r in embedding.requests] == ["query"]
    (query,) = search.queries
    assert query.text == "Python data platform"
    assert query.embedding_model_key == DOCUMENT_KEY
    assert query.terms == ("python",)
    assert query.sources == (DocumentKind.CV,)
    assert query.workspace_id == WS
