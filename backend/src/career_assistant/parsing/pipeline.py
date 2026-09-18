"""Document intake pipeline: admit → extract → span."""

from __future__ import annotations

import uuid
from datetime import datetime

from career_assistant.application.intake.admission import (
    AdmissionLimits,
    AdmittedBytes,
    admit_upload,
    enforce_parsed_limits,
)
from career_assistant.domain.documents import (
    Document,
    DocumentFormat,
    DocumentKind,
    Page,
    ParsedDocument,
    Span,
)
from career_assistant.domain.normalisation import paragraph_spans
from career_assistant.parsing.docx import extract_docx_pages
from career_assistant.parsing.pdf import extract_pdf_pages
from career_assistant.parsing.plain_text import extract_plain_text_pages


def parse_document(
    data: bytes,
    *,
    filename: str,
    kind: DocumentKind,
    document_id: str | None = None,
    parsed_at: datetime | None = None,
    declared_media_type: str | None = None,
    limits: AdmissionLimits | None = None,
) -> ParsedDocument:
    admitted = admit_upload(
        data,
        filename=filename,
        declared_media_type=declared_media_type,
        limits=limits,
    )
    return _build_parsed(
        admitted,
        kind=kind,
        document_id=document_id or str(uuid.uuid4()),
        parsed_at=parsed_at or datetime.now().astimezone(),
        limits=limits,
    )


def parse_pasted_text(
    text: str,
    *,
    filename: str = "pasted.txt",
    kind: DocumentKind,
    document_id: str | None = None,
    parsed_at: datetime | None = None,
    limits: AdmissionLimits | None = None,
) -> ParsedDocument:
    from career_assistant.application.intake.admission import admit_pasted_text

    admitted = admit_pasted_text(text, filename=filename, limits=limits)
    return _build_parsed(
        admitted,
        kind=kind,
        document_id=document_id or str(uuid.uuid4()),
        parsed_at=parsed_at or datetime.now().astimezone(),
        limits=limits,
    )


def _build_parsed(
    admitted: AdmittedBytes,
    *,
    kind: DocumentKind,
    document_id: str,
    parsed_at: datetime,
    limits: AdmissionLimits | None,
) -> ParsedDocument:
    pages_text = _extract_pages(admitted)
    enforce_parsed_limits(
        page_count=len(pages_text),
        character_count=sum(len(page) for page in pages_text),
        limits=limits,
    )

    pages: list[Page] = []
    spans: list[Span] = []
    for index, text in enumerate(pages_text, start=1):
        page = Page(document_id=document_id, page_number=index, text=text)
        pages.append(page)
        for start, end, span_text in paragraph_spans(text):
            spans.append(
                Span(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    page_number=index,
                    start_offset=start,
                    end_offset=end,
                    text=span_text,
                )
            )

    document = Document(
        id=document_id,
        kind=kind,
        filename=admitted.filename,
        format=admitted.format,
        page_count=len(pages),
        character_count=sum(len(page.text) for page in pages),
        parsed_at=parsed_at,
    )
    return ParsedDocument(
        document=document,
        pages=tuple(pages),
        spans=tuple(spans),
    )


def _extract_pages(admitted: AdmittedBytes) -> list[str]:
    if admitted.format == DocumentFormat.PLAIN_TEXT:
        return extract_plain_text_pages(admitted.data)
    if admitted.format == DocumentFormat.PDF:
        return extract_pdf_pages(admitted.data)
    if admitted.format == DocumentFormat.DOCX:
        return extract_docx_pages(admitted.data)
    raise AssertionError(f"unsupported format {admitted.format}")
