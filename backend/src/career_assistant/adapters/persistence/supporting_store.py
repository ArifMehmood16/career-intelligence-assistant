"""SQL-backed supporting cover-letter store for the production entrypoint."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.documents.cv import CvStore
from career_assistant.application.documents.supporting import (
    DownloadableDocument,
    SupportingDocumentView,
)
from career_assistant.application.ports.persistence import NewDocument, StoredDocument
from career_assistant.domain.documents import DocumentKind, Page, Span


class SqlSupportingDocumentStore:
    """SupportingDocumentStore over SqlUnitOfWork + optional CV download bridge."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], SqlUnitOfWork],
        cv_store: CvStore | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self.cv_store = cv_store

    def list_cover_letters(
        self, workspace_id: str
    ) -> tuple[SupportingDocumentView, ...]:
        with self._uow_factory() as uow:
            documents = uow.documents.list_cover_letters(workspace_id)
            return tuple(_to_view(document) for document in documents)

    def add_cover_letter(
        self, workspace_id: str, document: NewDocument
    ) -> SupportingDocumentView:
        if document.kind is not DocumentKind.COVER_LETTER:
            raise ValueError("supporting store only admits cover_letter documents")
        with self._uow_factory() as uow:
            uow.workspaces.ensure(workspace_id)
            stored = uow.documents.save_admitted(workspace_id, document)
            uow.commit()
            return _to_view(stored)

    def delete_cover_letter(self, workspace_id: str, document_id: str) -> bool:
        with self._uow_factory() as uow:
            document = uow.documents.get(workspace_id, document_id)
            if document is None or document.kind is not DocumentKind.COVER_LETTER:
                return False
            uow.documents.hard_delete(workspace_id, document_id)
            uow.commit()
            return True

    def get_downloadable(
        self, workspace_id: str, document_id: str
    ) -> DownloadableDocument | None:
        with self._uow_factory() as uow:
            document = uow.documents.get(workspace_id, document_id)
            if document is not None and document.kind is DocumentKind.COVER_LETTER:
                return DownloadableDocument(
                    id=document.id,
                    filename=document.filename,
                    media_type=document.media_type,
                    original_bytes=document.original_bytes,
                    kind=document.kind.value,
                )
        if self.cv_store is None:
            return None
        cv = self.cv_store.get_active(workspace_id)
        if cv is None or cv.view.id != document_id:
            return None
        return DownloadableDocument(
            id=cv.view.id,
            filename=cv.view.filename,
            media_type=cv.media_type,
            original_bytes=cv.original_bytes,
            kind=DocumentKind.CV.value,
        )

    def get_span(
        self, workspace_id: str, span_id: str
    ) -> tuple[Span, tuple[Page, ...]] | None:
        with self._uow_factory() as uow:
            found = uow.documents.find_span(workspace_id, span_id)
            if found is None:
                return None
            span, _pages = found
            document = uow.documents.get(workspace_id, span.document_id)
            if document is None or document.kind is not DocumentKind.COVER_LETTER:
                return None
            return found


def _to_view(document: StoredDocument) -> SupportingDocumentView:
    created = document.created_at
    updated = document.updated_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=UTC)
    return SupportingDocumentView(
        id=document.id,
        kind=document.kind.value,
        filename=document.filename,
        media_type=document.media_type,
        byte_length=document.byte_length,
        page_count=document.page_count,
        parsed_at=updated,
        created_at=created,
    )
