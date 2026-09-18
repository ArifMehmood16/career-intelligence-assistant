"""CV upload and lifecycle — admit, parse, store; no HTTP types here."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from career_assistant.application.intake.admission import AdmissionLimits
from career_assistant.application.intake.errors import IntakeError
from career_assistant.application.ports.persistence import NewDocument, ParseStatus
from career_assistant.domain.documents import DocumentFormat, DocumentKind, Page, Span
from career_assistant.parsing.pipeline import parse_pasted_text
from career_assistant.settings import LimitSettings

_MEDIA_TYPES = {
    DocumentFormat.PLAIN_TEXT: "text/plain",
    DocumentFormat.PDF: "application/pdf",
    DocumentFormat.DOCX: (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
}


@dataclass(frozen=True, slots=True)
class CvView:
    id: str
    filename: str
    page_count: int
    parsed_at: datetime
    reanalysis_job_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StoredCv:
    view: CvView
    spans: tuple[Span, ...]
    pages: tuple[Page, ...]
    normalised_text: str
    original_bytes: bytes
    media_type: str


class CvStore(Protocol):
    def get_active(self, workspace_id: str) -> StoredCv | None: ...

    def replace(self, workspace_id: str, document: NewDocument) -> StoredCv: ...

    def delete_active(self, workspace_id: str) -> None: ...

    def get_span(
        self, workspace_id: str, span_id: str
    ) -> tuple[Span, tuple[Page, ...]] | None: ...


class InMemoryCvStore:
    """Test-only CV store. Production path uses the SQL unit of work."""

    def __init__(self) -> None:
        self._by_workspace: dict[str, StoredCv] = {}
        self._spans: dict[tuple[str, str], tuple[Span, tuple[Page, ...]]] = {}

    def get_active(self, workspace_id: str) -> StoredCv | None:
        return self._by_workspace.get(workspace_id)

    def replace(self, workspace_id: str, document: NewDocument) -> StoredCv:
        now = datetime.now(UTC)
        pages = _pages_from_document(document)
        stored = StoredCv(
            view=CvView(
                id=document.id,
                filename=document.filename,
                page_count=document.page_count,
                parsed_at=now,
                reanalysis_job_ids=(),
            ),
            spans=document.spans,
            pages=pages,
            normalised_text=document.normalised_text,
            original_bytes=document.original_bytes,
            media_type=document.media_type,
        )
        previous = self._by_workspace.get(workspace_id)
        if previous is not None:
            for span in previous.spans:
                self._spans.pop((workspace_id, span.id), None)
        self._by_workspace[workspace_id] = stored
        for span in document.spans:
            self._spans[(workspace_id, span.id)] = (span, pages)
        return stored

    def delete_active(self, workspace_id: str) -> None:
        previous = self._by_workspace.pop(workspace_id, None)
        if previous is not None:
            for span in previous.spans:
                self._spans.pop((workspace_id, span.id), None)

    def get_span(
        self, workspace_id: str, span_id: str
    ) -> tuple[Span, tuple[Page, ...]] | None:
        return self._spans.get((workspace_id, span_id))


def _pages_from_document(document: NewDocument) -> tuple[Page, ...]:
    # Paste path stores one normalised blob; reconstruct page 1 for resolution.
    return (
        Page(
            document_id=document.id,
            page_number=1,
            text=document.normalised_text,
        ),
    )


def admission_limits_from(settings: LimitSettings) -> AdmissionLimits:
    return AdmissionLimits(
        max_upload_bytes=settings.max_upload_bytes,
        max_document_pages=settings.max_document_pages,
        max_document_chars=settings.max_document_chars,
    )


def upload_pasted_cv(
    store: CvStore,
    *,
    workspace_id: str,
    text: str,
    filename: str,
    limits: AdmissionLimits,
) -> CvView:
    parsed = parse_pasted_text(
        text,
        filename=filename or "pasted.txt",
        kind=DocumentKind.CV,
        limits=limits,
    )
    body = text.encode("utf-8")
    document = NewDocument(
        id=parsed.document.id,
        kind=DocumentKind.CV,
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
    stored = store.replace(workspace_id, document)
    return stored.view


def get_cv(store: CvStore, *, workspace_id: str) -> CvView | None:
    stored = store.get_active(workspace_id)
    return None if stored is None else stored.view


def delete_cv(store: CvStore, *, workspace_id: str) -> None:
    store.delete_active(workspace_id)


def reraise_intake_as_message(error: IntakeError) -> tuple[str, str, int]:
    """Map intake codes to HTTP status + contract code/message."""
    status = {
        "document_too_large": 413,
        "document_unsupported": 415,
        "document_unreadable": 422,
    }[error.code.value]
    return error.code.value, error.message, status
