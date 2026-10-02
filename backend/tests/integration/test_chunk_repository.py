"""PLAN 18.10 — validated chunks and their vectors round-trip through PostgreSQL."""

from __future__ import annotations

import uuid

import pytest
from tests.integration.conftest import make_document
from tests.support.v2_chunks import CV, JD, cv_chunks, jd_chunks

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ports.chunks import (
    ChunkProvenance,
    ChunkVector,
    EmbeddingModel,
)
from career_assistant.domain.documents import DocumentKind

pytestmark = pytest.mark.integration

PROVENANCE = ChunkProvenance("hermetic", "rules-v1", "chunking-v1")
DOCUMENT_MODEL = EmbeddingModel("hermetic", "lexical-v1", 3, "document")


def _document(uow: SqlUnitOfWork, kind: DocumentKind, text: str) -> tuple[str, str]:
    ws = str(uuid.uuid4())
    with uow:
        uow.workspaces.ensure(ws)
        doc = uow.documents.save_admitted(ws, make_document(kind=kind, text=text))
        uow.commit()
    return ws, doc.id


def test_cv_chunks_round_trip_with_roles_terms_and_context(uow: SqlUnitOfWork) -> None:
    ws, doc = _document(uow, DocumentKind.CV, CV)
    chunks = cv_chunks()

    with uow:
        uow.chunks.replace_chunks(ws, doc, chunks, PROVENANCE)
        uow.commit()
    with uow:
        found = uow.chunks.find_chunks(ws, doc, prompt_version="chunking-v1")

    assert tuple(stored.chunk for stored in found) == chunks
    assert {stored.document_id for stored in found} == {doc}


def test_advert_requirements_round_trip(uow: SqlUnitOfWork) -> None:
    ws, doc = _document(uow, DocumentKind.JOB_DESCRIPTION, JD)
    chunks = jd_chunks()

    with uow:
        uow.chunks.replace_chunks(ws, doc, chunks, PROVENANCE)
        uow.commit()
    with uow:
        found = uow.chunks.find_chunks(ws, doc, prompt_version="chunking-v1")

    assert tuple(stored.chunk for stored in found) == chunks


def test_another_prompt_version_finds_nothing(uow: SqlUnitOfWork) -> None:
    ws, doc = _document(uow, DocumentKind.CV, CV)
    with uow:
        uow.chunks.replace_chunks(ws, doc, cv_chunks(), PROVENANCE)
        uow.commit()

    with uow:
        assert uow.chunks.find_chunks(ws, doc, prompt_version="chunking-v2") == ()


def test_replacing_removes_the_previous_chunks(uow: SqlUnitOfWork) -> None:
    ws, doc = _document(uow, DocumentKind.CV, CV)
    with uow:
        uow.chunks.replace_chunks(ws, doc, cv_chunks(), PROVENANCE)
        uow.commit()

    with uow:
        again = uow.chunks.replace_chunks(ws, doc, cv_chunks()[:1], PROVENANCE)
        uow.commit()
    with uow:
        found = uow.chunks.find_chunks(ws, doc, prompt_version="chunking-v1")

    assert [stored.chunk_id for stored in found] == [again[0].chunk_id]


def test_vectors_are_kept_per_model_key(uow: SqlUnitOfWork) -> None:
    ws, doc = _document(uow, DocumentKind.CV, CV)
    with uow:
        stored = uow.chunks.replace_chunks(ws, doc, cv_chunks(), PROVENANCE)
        uow.chunks.save_vectors(
            ws, DOCUMENT_MODEL, [ChunkVector(stored[1].chunk_id, (0.1, 0.2, 0.3))]
        )
        uow.commit()

    with uow:
        embedded = uow.chunks.embedded_chunk_ids(ws, doc, DOCUMENT_MODEL.key)
        other = uow.chunks.embedded_chunk_ids(ws, doc, "other:model:3:document")

    assert embedded == {stored[1].chunk_id}
    assert other == frozenset()


def test_load_chunks_is_scoped_to_the_workspace(uow: SqlUnitOfWork) -> None:
    ws, doc = _document(uow, DocumentKind.CV, CV)
    with uow:
        stored = uow.chunks.replace_chunks(ws, doc, cv_chunks(), PROVENANCE)
        uow.commit()
    ids = [s.chunk_id for s in stored]

    with uow:
        mine = uow.chunks.load_chunks(ws, ids)
        theirs = uow.chunks.load_chunks(str(uuid.uuid4()), ids)

    assert [s.chunk_id for s in mine] == ids
    assert theirs == ()
