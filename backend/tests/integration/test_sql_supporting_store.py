"""Phase 13 — SqlSupportingDocumentStore persists cover letters in PostgreSQL."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.supporting_store import (
    SqlSupportingDocumentStore,
)
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.documents.cv import (
    admission_limits_from,
    upload_pasted_cv,
)
from career_assistant.application.documents.supporting import (
    upload_pasted_cover_letter,
)
from career_assistant.domain.documents import DocumentKind
from career_assistant.settings import LimitSettings

pytestmark = pytest.mark.integration

_LETTER = """Dear Hiring Manager,

I am applying for the Analytics Engineer role. I owned dbt models in production.

Kind regards
"""


def test_sql_supporting_store_upload_list_delete_and_cv_download(
    session_factory: sessionmaker[Session],
) -> None:
    def uow_factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    cv_store = SqlCvStore(uow_factory)
    store = SqlSupportingDocumentStore(uow_factory=uow_factory, cv_store=cv_store)
    workspace_id = str(uuid.uuid4())
    limits = admission_limits_from(LimitSettings())

    assert store.list_cover_letters(workspace_id) == ()

    view = upload_pasted_cover_letter(
        store,
        workspace_id=workspace_id,
        text=_LETTER,
        filename="previous-letter.txt",
        limits=limits,
    )
    assert view.kind == DocumentKind.COVER_LETTER.value
    assert view.filename == "previous-letter.txt"

    listed = store.list_cover_letters(workspace_id)
    assert len(listed) == 1
    assert listed[0].id == view.id

    downloaded = store.get_downloadable(workspace_id, view.id)
    assert downloaded is not None
    assert downloaded.original_bytes == _LETTER.encode("utf-8")
    assert downloaded.kind == DocumentKind.COVER_LETTER.value

    # CV download still bridges through the supporting store.
    cv = upload_pasted_cv(
        cv_store,
        workspace_id=workspace_id,
        text="Owned dbt models in production.",
        filename="cv.txt",
        limits=limits,
    )
    cv_dl = store.get_downloadable(workspace_id, cv.id)
    assert cv_dl is not None
    assert cv_dl.kind == DocumentKind.CV.value
    assert b"Owned dbt" in cv_dl.original_bytes

    assert store.delete_cover_letter(workspace_id, view.id) is True
    assert store.list_cover_letters(workspace_id) == ()
    assert store.get_downloadable(workspace_id, view.id) is None
    assert store.delete_cover_letter(workspace_id, view.id) is False
