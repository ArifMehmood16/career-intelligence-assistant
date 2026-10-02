"""PLAN 18.10 — a document is chunked, graphed and embedded once, then reused."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import BaseModel
from tests.support.in_memory_index import InMemoryIndexStore

from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.application.chunking.service import (
    ChunkingRequest,
    DocumentChunker,
)
from career_assistant.application.indexing.service import (
    DocumentIndexer,
    IndexedDocument,
)
from career_assistant.application.ports.structured import (
    StructuredRequest,
    StructuredResult,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    EmbeddingRequest,
    EmbeddingResult,
)
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.knowledge_graph import (
    DocumentGraph,
    graph_from_chunks,
)

FIXTURES = Path(__file__).resolve().parents[3] / "sample-data" / "fixtures"
DOCUMENT_KEY = "hermetic:lexical-hash-v1:64:document"


class CountingStructured:
    def __init__(self) -> None:
        self._inner = HermeticStructuredCompleter()
        self.calls = 0

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete_structured[T: BaseModel](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]:
        self.calls += 1
        return self._inner.complete_structured(request)


class RecordingEmbedding:
    def __init__(self) -> None:
        self._inner = HermeticEmbeddingAdapter()
        self.requests: list[EmbeddingRequest] = []

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.requests.append(request)
        return self._inner.embed(request)

    @property
    def texts(self) -> int:
        return sum(len(r.texts) for r in self.requests)


def _world() -> tuple[
    DocumentIndexer, InMemoryIndexStore, CountingStructured, RecordingEmbedding
]:
    store = InMemoryIndexStore()
    structured = CountingStructured()
    embedding = RecordingEmbedding()
    indexer = DocumentIndexer(
        chunker=DocumentChunker(structured),
        embedding=embedding,
        store=store,
        max_chars_per_text=8_000,
    )
    return indexer, store, structured, embedding


def _graph_of(indexed: IndexedDocument) -> DocumentGraph:
    """The chunks' own graph plus what the taxonomist says about its terms."""
    source = CV if indexed.chunks[0].document_id == CV.document_id else JD
    outcome = DocumentChunker(HermeticStructuredCompleter()).chunk(source)
    return graph_from_chunks(outcome.chunks).with_inferred(outcome.inferred_edges)


def _request(kind: DocumentKind, name: str, document_id: str) -> ChunkingRequest:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return ChunkingRequest(document_id=document_id, kind=kind, text=text)


CV = _request(DocumentKind.CV, "resumes/cv-strong-match.txt", "cv-1")
JD = _request(
    DocumentKind.JOB_DESCRIPTION, "job-descriptions/jd-clean-match.txt", "jd-1"
)


def test_first_index_chunks_graphs_and_embeds_the_evidence() -> None:
    indexer, store, _, embedding = _world()

    indexed = indexer.index("ws", CV)

    assert indexed.chunks and not indexed.reused
    assert store.graphs["cv-1"] == _graph_of(indexed)
    eligible = {s.chunk_id for s in indexed.chunks if s.chunk.evidence_eligible}
    assert eligible
    assert store.embedded_chunk_ids("ws", "cv-1", DOCUMENT_KEY) == eligible
    assert {r.input_type for r in embedding.requests} == {"document"}
    assert len(embedding.requests) == 1


def test_a_second_index_reuses_the_chunks_and_vectors() -> None:
    indexer, store, structured, embedding = _world()
    first = indexer.index("ws", CV)
    calls, texts = structured.calls, embedding.texts

    second = indexer.index("ws", CV)

    assert second.reused
    assert [s.chunk_id for s in second.chunks] == [s.chunk_id for s in first.chunks]
    assert structured.calls == calls
    assert embedding.texts == texts


def test_an_advert_is_graphed_but_never_embedded() -> None:
    indexer, store, _, embedding = _world()

    indexed = indexer.index("ws", JD)

    assert any(s.chunk.atomic_requirements for s in indexed.chunks)
    assert store.graphs["jd-1"] == _graph_of(indexed)
    assert embedding.requests == []


def test_concurrent_roles_reuse_one_cv_index() -> None:
    indexer, _, structured, embedding = _world()
    with ThreadPoolExecutor(max_workers=2) as threads:
        first, second = list(threads.map(lambda _: indexer.index("ws", CV), (1, 2)))
    assert structured.calls == 1
    assert len(embedding.requests) == 1
    assert first.chunks == second.chunks
    assert sorted((first.reused, second.reused)) == [False, True]
