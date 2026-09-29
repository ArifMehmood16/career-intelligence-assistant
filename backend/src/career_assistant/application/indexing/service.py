"""Chunk, graph and embed a document once, then reuse it (ADR 013, PLAN 18.10).

A document already chunked under the current chunking prompt is not sent to the
model again. Only evidence-eligible chunks are embedded, as documents; a vector
already stored under the same model key is not computed twice.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from career_assistant.application.chunking.prompts import CHUNKING_PROMPT_VERSION
from career_assistant.application.chunking.service import (
    ChunkingRequest,
    DocumentChunker,
)
from career_assistant.application.graph.taxonomy import TermTaxonomist
from career_assistant.application.ports.chunks import (
    ChunkProvenance,
    ChunkVector,
    DocumentIndexStore,
    EmbeddingModel,
    StoredChunk,
)
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.types import EmbeddingRequest, EmbeddingResult
from career_assistant.domain.chunking import retrieval_text
from career_assistant.domain.knowledge_graph import NodeKind, graph_from_chunks


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
        taxonomist: TermTaxonomist,
        embedding: EmbeddingPort,
        store: DocumentIndexStore,
        max_chars_per_text: int,
    ) -> None:
        self._chunker = chunker
        self._taxonomist = taxonomist
        self._embedding = embedding
        self._store = store
        self._max_chars = max_chars_per_text

    def index(self, workspace_id: str, request: ChunkingRequest) -> IndexedDocument:
        stored = self._store.find_chunks(
            workspace_id, request.document_id, prompt_version=CHUNKING_PROMPT_VERSION
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
        terms = [n.key.name for n in graph.nodes if n.key.kind is NodeKind.TECHNOLOGY]
        taxonomy = self._taxonomist.relate(terms)
        stored = self._store.save_document(
            workspace_id,
            request.document_id,
            outcome.chunks,
            ChunkProvenance(
                outcome.provider_id, outcome.model_tag, outcome.prompt_version
            ),
            graph.with_inferred(taxonomy.edges),
        )
        return stored, outcome.left_machine or taxonomy.left_machine

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
        probe = self._vectors([eligible[0][1]])
        model = _document_model(probe)
        done = self._store.embedded_chunk_ids(workspace_id, document_id, model.key)
        missing = [(cid, text) for cid, text in eligible if cid not in done]
        if not missing:
            return probe.left_machine
        rest = [item for item in missing if item[0] != eligible[0][0]]
        vectors = {eligible[0][0]: probe.vectors[0]}
        left_machine = probe.left_machine
        if rest:
            result = self._vectors([text for _, text in rest])
            vectors.update(zip((cid for cid, _ in rest), result.vectors, strict=True))
            left_machine = left_machine or result.left_machine
        self._store.save_vectors(
            workspace_id,
            model,
            [ChunkVector(cid, vectors[cid]) for cid, _ in missing],
        )
        return left_machine

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
