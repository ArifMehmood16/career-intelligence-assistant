"""Supporting cover-letter documents — admit, store, list, delete, download."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from career_assistant.application.documents.cv import (
    CvStore,
    StoredCv,
    admission_limits_from,
    reraise_intake_as_message,
)
from career_assistant.application.intake.admission import AdmissionLimits
from career_assistant.application.intake.errors import IntakeError
from career_assistant.application.ports.persistence import NewDocument, ParseStatus
from career_assistant.domain.documents import DocumentFormat, DocumentKind, Page, Span
from career_assistant.logconfig import log_event
from career_assistant.parsing.pipeline import parse_pasted_text
from career_assistant.settings import LimitSettings

_log = logging.getLogger(__name__)

_MEDIA_TYPES = {
    DocumentFormat.PLAIN_TEXT: "text/plain",
    DocumentFormat.PDF: "application/pdf",
    DocumentFormat.DOCX: (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
}


@dataclass(frozen=True, slots=True)
class SupportingDocumentView:
    id: str
    kind: str
    filename: str
    media_type: str
    byte_length: int
    page_count: int
    parsed_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StoredSupportingDocument:
    view: SupportingDocumentView
    spans: tuple[Span, ...]
    pages: tuple[Page, ...]
    normalised_text: str
    original_bytes: bytes


@dataclass(frozen=True, slots=True)
class DownloadableDocument:
    id: str
    filename: str
    media_type: str
    original_bytes: bytes
    kind: str


class SupportingDocumentStore(Protocol):
    def list_cover_letters(
        self, workspace_id: str
    ) -> tuple[SupportingDocumentView, ...]: ...

    def add_cover_letter(
        self, workspace_id: str, document: NewDocument
    ) -> SupportingDocumentView: ...

    def delete_cover_letter(self, workspace_id: str, document_id: str) -> bool: ...

    def get_downloadable(
        self, workspace_id: str, document_id: str
    ) -> DownloadableDocument | None: ...

    def get_span(
        self, workspace_id: str, span_id: str
    ) -> tuple[Span, tuple[Page, ...]] | None: ...

    def spans_for_workspace(self, workspace_id: str) -> tuple[Span, ...]: ...


@dataclass
class InMemorySupportingDocumentStore:
    """Hermetic store for uploaded cover letters (+ optional CV download bridge)."""

    cv_store: CvStore | None = None
    _letters: dict[str, dict[str, StoredSupportingDocument]] = field(
        default_factory=dict
    )

    def list_cover_letters(
        self, workspace_id: str
    ) -> tuple[SupportingDocumentView, ...]:
        items = self._letters.get(workspace_id, {})
        return tuple(
            sorted(
                (stored.view for stored in items.values()),
                key=lambda view: view.created_at.isoformat(),
            )
        )

    def add_cover_letter(
        self, workspace_id: str, document: NewDocument
    ) -> SupportingDocumentView:
        now = datetime.now(UTC)
        pages = (
            Page(
                document_id=document.id,
                page_number=1,
                text=document.normalised_text,
            ),
        )
        stored = StoredSupportingDocument(
            view=SupportingDocumentView(
                id=document.id,
                kind=DocumentKind.COVER_LETTER.value,
                filename=document.filename,
                media_type=document.media_type,
                byte_length=len(document.original_bytes),
                page_count=document.page_count,
                parsed_at=now,
                created_at=now,
            ),
            spans=document.spans,
            pages=pages,
            normalised_text=document.normalised_text,
            original_bytes=document.original_bytes,
        )
        self._letters.setdefault(workspace_id, {})[document.id] = stored
        return stored.view

    def delete_cover_letter(self, workspace_id: str, document_id: str) -> bool:
        items = self._letters.get(workspace_id, {})
        if document_id not in items:
            return False
        del items[document_id]
        log_event(_log, "cover_letter.deleted", document_id=document_id)
        return True

    def get_downloadable(
        self, workspace_id: str, document_id: str
    ) -> DownloadableDocument | None:
        letter = self._letters.get(workspace_id, {}).get(document_id)
        if letter is not None:
            return DownloadableDocument(
                id=letter.view.id,
                filename=letter.view.filename,
                media_type=letter.view.media_type,
                original_bytes=letter.original_bytes,
                kind=letter.view.kind,
            )
        if self.cv_store is None:
            return None
        cv: StoredCv | None = self.cv_store.get_active(workspace_id)
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
        for stored in self._letters.get(workspace_id, {}).values():
            for span in stored.spans:
                if span.id == span_id:
                    return span, stored.pages
        return None

    def spans_for_workspace(self, workspace_id: str) -> tuple[Span, ...]:
        spans: list[Span] = []
        for stored in self._letters.get(workspace_id, {}).values():
            spans.extend(stored.spans)
        return tuple(spans)


def upload_pasted_cover_letter(
    store: SupportingDocumentStore,
    *,
    workspace_id: str,
    text: str,
    filename: str,
    limits: AdmissionLimits,
) -> SupportingDocumentView:
    parsed = parse_pasted_text(
        text,
        filename=filename or "cover-letter.txt",
        kind=DocumentKind.COVER_LETTER,
        limits=limits,
    )
    body = text.encode("utf-8")
    return _store_parsed_cover_letter(
        store, workspace_id=workspace_id, parsed=parsed, body=body
    )


def upload_bytes_cover_letter(
    store: SupportingDocumentStore,
    *,
    workspace_id: str,
    data: bytes,
    filename: str,
    declared_media_type: str | None,
    limits: AdmissionLimits,
) -> SupportingDocumentView:
    from career_assistant.parsing.pipeline import parse_document

    parsed = parse_document(
        data,
        filename=filename or "cover-letter",
        kind=DocumentKind.COVER_LETTER,
        declared_media_type=declared_media_type,
        limits=limits,
    )
    return _store_parsed_cover_letter(
        store, workspace_id=workspace_id, parsed=parsed, body=data
    )


def _store_parsed_cover_letter(
    store: SupportingDocumentStore,
    *,
    workspace_id: str,
    parsed: object,
    body: bytes,
) -> SupportingDocumentView:
    from career_assistant.domain.documents import ParsedDocument

    assert isinstance(parsed, ParsedDocument)
    document = NewDocument(
        id=parsed.document.id,
        kind=DocumentKind.COVER_LETTER,
        filename=parsed.document.filename,
        media_type=_MEDIA_TYPES[parsed.document.format],
        original_bytes=body,
        sha256=hashlib.sha256(body).hexdigest(),
        normalised_text="\n\n".join(page.text for page in parsed.pages),
        parse_status=ParseStatus.PARSED,
        page_count=parsed.document.page_count,
        character_count=parsed.document.character_count,
        is_active=True,
        spans=parsed.spans,
    )
    view = store.add_cover_letter(workspace_id, document)
    log_event(
        _log,
        "cover_letter.uploaded",
        document_id=view.id,
        page_count=view.page_count,
        span_count=len(document.spans),
        byte_length=view.byte_length,
        media_type=view.media_type,
    )
    return view


def limits_from(settings: LimitSettings) -> AdmissionLimits:
    return admission_limits_from(settings)


__all__ = [
    "DownloadableDocument",
    "InMemorySupportingDocumentStore",
    "SupportingDocumentStore",
    "SupportingDocumentView",
    "IntakeError",
    "limits_from",
    "reraise_intake_as_message",
    "upload_bytes_cover_letter",
    "upload_pasted_cover_letter",
]
