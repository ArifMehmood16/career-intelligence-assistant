"""Span resolution — highlight is always an exact substring of the paragraph."""

from __future__ import annotations

from career_assistant.domain.documents import Evidence, Page, Span


class SpanNotFoundError(LookupError):
    pass


def resolve_span(
    span: Span,
    pages: tuple[Page, ...] | list[Page],
) -> Evidence:
    page = next(
        (p for p in pages if p.page_number == span.page_number),
        None,
    )
    if page is None or page.document_id != span.document_id:
        raise SpanNotFoundError(span.id)

    if span.end_offset > len(page.text) or span.start_offset > len(page.text):
        raise SpanNotFoundError(span.id)

    slice_text = page.text[span.start_offset : span.end_offset]
    if slice_text != span.text:
        raise SpanNotFoundError(span.id)

    paragraph = _containing_paragraph(page.text, span.start_offset, span.end_offset)
    if span.text not in paragraph:
        raise SpanNotFoundError(span.id)

    return Evidence(
        document_id=span.document_id,
        page=span.page_number,
        paragraph=paragraph,
        highlight=span.text,
    )


def _containing_paragraph(page_text: str, start: int, end: int) -> str:
    before = page_text.rfind("\n\n", 0, start)
    after = page_text.find("\n\n", end)
    left = 0 if before < 0 else before + 2
    right = len(page_text) if after < 0 else after
    return page_text[left:right]
