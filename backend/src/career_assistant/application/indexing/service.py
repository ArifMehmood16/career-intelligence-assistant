"""Chunk, graph and embed a document once, then reuse it (ADR 013, PLAN 18.10).

A document already chunked under the current chunking prompt is not sent to the
model again. Only evidence-eligible chunks are embedded, as documents; a vector
already stored under the same model key is not computed twice.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
from weakref import WeakValueDictionary

from career_assistant.application.chunking.prompts import CHUNKING_PROMPT_VERSION
from career_assistant.application.chunking.service import (
    ChunkingRequest,
    DocumentChunker,
)
from career_assistant.application.ports.chunks import (
    ChunkProvenance,
    ChunkVector,
    DocumentIndexStore,
    EmbeddingModel,
    StoredChunk,
)
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.progress import plan_calls
from career_assistant.application.ports.types import EmbeddingRequest, EmbeddingResult
from career_assistant.domain.chunking import retrieval_text
from career_assistant.domain.knowledge_graph import graph_from_chunks


@dataclass(frozen=True, slots=True)
class IndexedDocument:
    chunks: tuple[StoredChunk, ...]
    reused: bool
    left_machine: bool


class DocumentIndexer:
    def __init__(
        self,
        *,
        chunker: DocumentChunker,
        embedding: EmbeddingPort,
        store: DocumentIndexStore,
        max_chars_per_text: int,
    ) -> None:
        self._chunker = chunker
        self._embedding = embedding
        self._store = store
        self._max_chars = max_chars_per_text

    @property
    def concurrency(self) -> int:
        return self._chunker.concurrency

    def index(self, workspace_id: str, request: ChunkingRequest) -> IndexedDocument:
        plan_calls()
        with _document_lock(workspace_id, request.document_id):
            stored = self._store.find_chunks(
                workspace_id,
                request.document_id,
                prompt_version=CHUNKING_PROMPT_VERSION,
            )
            reused = bool(stored)
            left_machine = False
            if not reused:
                stored, left_machine = self._chunk(workspace_id, request)
            embedded_remotely = self._embed(workspace_id, request.document_id, stored)
            return IndexedDocument(
                chunks=stored,
                reused=reused,
                left_machine=left_machine or embedded_remotely,
            )

    def _chunk(
        self, workspace_id: str, request: ChunkingRequest
    ) -> tuple[tuple[StoredChunk, ...], bool]:
        outcome = self._chunker.chunk(request)
        graph = graph_from_chunks(outcome.chunks)
        stored = self._store.save_document(
            workspace_id,
            request.document_id,
            outcome.chunks,
            ChunkProvenance(
                outcome.provider_id, outcome.model_tag, outcome.prompt_version
            ),
            graph.with_inferred(outcome.inferred_edges),
        )
        return stored, outcome.left_machine

    def _embed(
        self, workspace_id: str, document_id: str, stored: Sequence[StoredChunk]
    ) -> bool:
        eligible = [
            (s.chunk_id, text)
            for s in stored
            if s.chunk.evidence_eligible and (text := retrieval_text(s.chunk))
        ]
        if not eligible:
            return False
        capabilities = self._embedding.capabilities
        done: frozenset[str] = frozenset()
        if capabilities.model_tag and capabilities.embedding_dimensions:
            model = EmbeddingModel(
                capabilities.provider_id,
                capabilities.model_tag,
                capabilities.embedding_dimensions,
                "document",
            )
            done = self._store.embedded_chunk_ids(workspace_id, document_id, model.key)
        missing = [(cid, text) for cid, text in eligible if cid not in done]
        if not missing:
            return False
        plan_calls(embedding=1)
        result = self._vectors([text for _, text in missing])
        self._store.save_vectors(
            workspace_id,
            _document_model(result),
            [
                ChunkVector(cid, vector)
                for (cid, _), vector in zip(missing, result.vectors, strict=True)
            ],
        )
        return result.left_machine

    def _vectors(self, texts: Sequence[str]) -> EmbeddingResult:
        return self._embedding.embed(
            EmbeddingRequest(
                texts=tuple(texts),
                max_chars_per_text=self._max_chars,
                input_type="document",
            )
        )


def _document_model(result: EmbeddingResult) -> EmbeddingModel:
    return EmbeddingModel(
        result.provider_id, result.model_tag, result.dimensions, "document"
    )


_document_locks: WeakValueDictionary[tuple[str, str], Lock] = WeakValueDictionary()
_document_locks_guard = Lock()


@contextmanager
def _document_lock(workspace_id: str, document_id: str) -> Iterator[None]:
    """Overlapping roles reuse one CV index; idle locks hold no document state."""
    key = (workspace_id, document_id)
    with _document_locks_guard:
        lock = _document_locks.get(key)
        if lock is None:
            lock = Lock()
            _document_locks[key] = lock
    with lock:
        yield
