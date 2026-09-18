"""SQL-backed CvStore — production persistence for the CV paste lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.documents.cv import CvView, StoredCv
from career_assistant.application.ports.persistence import NewDocument, StoredDocument
from career_assistant.domain.documents import Page, Span


class SqlCvStore:
    """CvStore over SqlUnitOfWork. Each method opens its own unit of work."""

    def __init__(self, uow_factory: Callable[[], SqlUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def get_active(self, workspace_id: str) -> StoredCv | None:
        with self._uow_factory() as uow:
            document = uow.documents.get_active_cv(workspace_id)
            if document is None:
                return None
            spans = uow.documents.list_spans(workspace_id, document.id)
            return _to_stored_cv(document, spans)

    def replace(self, workspace_id: str, document: NewDocument) -> StoredCv:
        with self._uow_factory() as uow:
            uow.workspaces.ensure(workspace_id)
            stored = uow.documents.replace_cv(workspace_id, document)
            spans = uow.documents.list_spans(workspace_id, stored.id)
            uow.commit()
            return _to_stored_cv(stored, spans)

    def delete_active(self, workspace_id: str) -> None:
        with self._uow_factory() as uow:
            document = uow.documents.get_active_cv(workspace_id)
            if document is None:
                return
            uow.documents.hard_delete(workspace_id, document.id)
            uow.commit()

    def get_span(
        self, workspace_id: str, span_id: str
    ) -> tuple[Span, tuple[Page, ...]] | None:
        active = self.get_active(workspace_id)
        if active is None:
            return None
        for span in active.spans:
            if span.id == span_id:
                return span, active.pages
        return None


def _to_stored_cv(document: StoredDocument, spans: tuple[Span, ...]) -> StoredCv:
    pages = (
        Page(
            document_id=document.id,
            page_number=1,
            text=document.normalised_text,
        ),
    )
    parsed_at = document.updated_at
    if parsed_at.tzinfo is None:
        parsed_at = parsed_at.replace(tzinfo=UTC)
    return StoredCv(
        view=CvView(
            id=document.id,
            filename=document.filename,
            page_count=document.page_count,
            parsed_at=parsed_at,
            reanalysis_job_ids=(),
        ),
        spans=spans,
        pages=pages,
        normalised_text=document.normalised_text,
        original_bytes=document.original_bytes,
        media_type=document.media_type,
    )
