"""PostgreSQL integration fixtures — never share DATABASE_URL with tests."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.engine import create_db_engine
from career_assistant.adapters.persistence.migrate import downgrade_base, upgrade_head
from career_assistant.adapters.persistence.schema import APP_SCHEMA
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ports.persistence import NewDocument, ParseStatus
from career_assistant.domain.documents import DocumentKind, Span
from career_assistant.settings import DatabaseSettings


@pytest.fixture(scope="session")
def database_settings() -> DatabaseSettings:
    settings = DatabaseSettings()
    if settings.test_database_url == settings.database_url:
        pytest.fail("TEST_DATABASE_URL must differ from DATABASE_URL")
    return settings


@pytest.fixture(scope="session")
def migrated_engine(database_settings: DatabaseSettings) -> Iterator[Engine]:
    url = database_settings.test_database_url
    downgrade_base(url)
    upgrade_head(url)
    engine = create_db_engine(database_settings, url=url)
    yield engine
    downgrade_base(url)
    engine.dispose()


@pytest.fixture()
def session_factory(migrated_engine: Engine) -> Iterator[sessionmaker[Session]]:
    factory = sessionmaker(
        bind=migrated_engine, autoflush=False, expire_on_commit=False
    )
    # Truncate between tests while keeping the dedicated application schema.
    with migrated_engine.begin() as conn:
        conn.execute(
            text(
                f"TRUNCATE TABLE "
                f"{APP_SCHEMA}.mapping_spans, {APP_SCHEMA}.mappings, "
                f"{APP_SCHEMA}.draft_citations, {APP_SCHEMA}.answer_citations, "
                f"{APP_SCHEMA}.score_explanations, {APP_SCHEMA}.requirements, "
                f"{APP_SCHEMA}.generated_drafts, {APP_SCHEMA}.embeddings, "
                f"{APP_SCHEMA}.claim_spans, {APP_SCHEMA}.answers, "
                f"{APP_SCHEMA}.analysis_jobs, {APP_SCHEMA}.spans, "
                f"{APP_SCHEMA}.roles, {APP_SCHEMA}.questions, "
                f"{APP_SCHEMA}.claims, "
                f"{APP_SCHEMA}.provider_settings, "
                f"{APP_SCHEMA}.provider_call_accounting, "
                f"{APP_SCHEMA}.documents, {APP_SCHEMA}.conversations, "
                f"{APP_SCHEMA}.workspaces "
                f"RESTART IDENTITY CASCADE"
            )
        )
    yield factory


@pytest.fixture()
def uow(session_factory: sessionmaker[Session]) -> SqlUnitOfWork:
    return SqlUnitOfWork(session_factory)


def make_document(
    *,
    kind: DocumentKind = DocumentKind.CV,
    text: str = "Owned dbt pipelines.",
    is_active: bool = True,
    span_text: str | None = None,
) -> NewDocument:
    doc_id = str(uuid.uuid4())
    body = text.encode("utf-8")
    excerpt = span_text or text
    span = Span(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        page_number=1,
        start_offset=0,
        end_offset=len(excerpt),
        text=excerpt,
    )
    return NewDocument(
        id=doc_id,
        kind=kind,
        filename="cv.txt" if kind is DocumentKind.CV else f"{kind.value}.txt",
        media_type="text/plain",
        original_bytes=body,
        sha256=hashlib.sha256(body).hexdigest(),
        normalised_text=text,
        parse_status=ParseStatus.PARSED,
        page_count=1,
        character_count=len(text),
        is_active=is_active,
        spans=(span,),
    )
