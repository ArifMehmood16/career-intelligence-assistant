"""PLAN 18.10 — the indexer's store writes chunks and graph in one transaction."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.conftest import make_document

from career_assistant.adapters.persistence.index_store import SqlDocumentIndexStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
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
from career_assistant.application.indexing.service import DocumentIndexer
from career_assistant.domain.documents import DocumentKind

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[3] / "sample-data" / "fixtures"
DOCUMENT_KEY = "hermetic:lexical-hash-v1:64:document"


def test_an_indexed_cv_is_stored_graphed_embedded_and_reused(
    session_factory: sessionmaker[Session],
) -> None:
    text = (FIXTURES / "resumes" / "cv-strong-match.txt").read_text(encoding="utf-8")
    uow = SqlUnitOfWork(session_factory)
    ws = str(uuid.uuid4())
    with uow:
        uow.workspaces.ensure(ws)
        cv = uow.documents.save_admitted(ws, make_document(text=text))
        uow.commit()
    store = SqlDocumentIndexStore(lambda: SqlUnitOfWork(session_factory))
    structured = HermeticStructuredCompleter()
    indexer = DocumentIndexer(
        chunker=DocumentChunker(structured),
        embedding=HermeticEmbeddingAdapter(),
        store=store,
        max_chars_per_text=8_000,
    )
    request = ChunkingRequest(document_id=cv.id, kind=DocumentKind.CV, text=text)

    first = indexer.index(ws, request)
    second = indexer.index(ws, request)

    eligible = {s.chunk_id for s in first.chunks if s.chunk.evidence_eligible}
    assert eligible
    assert store.embedded_chunk_ids(ws, cv.id, DOCUMENT_KEY) == eligible
    assert second.reused
    assert [s.chunk_id for s in second.chunks] == [s.chunk_id for s in first.chunks]
    with uow:
        assert uow.graph.known_technologies(ws)
