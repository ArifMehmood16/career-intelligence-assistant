"""Phase 11.8 — SqlCvStore implements CvStore over PostgreSQL."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.documents.cv import (
    admission_limits_from,
    delete_cv,
    get_cv,
    upload_pasted_cv,
)
from career_assistant.settings import LimitSettings

pytestmark = pytest.mark.integration


def test_sql_cv_store_upload_get_span_and_delete(
    session_factory: sessionmaker[Session],
) -> None:
    store = SqlCvStore(lambda: SqlUnitOfWork(session_factory))
    workspace_id = str(uuid.uuid4())
    limits = admission_limits_from(LimitSettings())

    view = upload_pasted_cv(
        store,
        workspace_id=workspace_id,
        text="Owned dbt models in production for the warehouse.",
        filename="cv.txt",
        limits=limits,
    )
    assert view.filename == "cv.txt"
    assert view.page_count >= 1

    fetched = get_cv(store, workspace_id=workspace_id)
    assert fetched is not None
    assert fetched.id == view.id

    active = store.get_active(workspace_id)
    assert active is not None
    assert active.normalised_text.startswith("Owned dbt")
    assert active.spans
    span_id = active.spans[0].id

    resolved = store.get_span(workspace_id, span_id)
    assert resolved is not None
    span, pages = resolved
    assert span.id == span_id
    assert pages
    assert span.text in pages[0].text

    delete_cv(store, workspace_id=workspace_id)
    assert get_cv(store, workspace_id=workspace_id) is None
    assert store.get_span(workspace_id, span_id) is None
