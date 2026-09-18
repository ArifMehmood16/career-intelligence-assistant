"""Document, page and span — the citation unit for the product."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DocumentKind(StrEnum):
    CV = "cv"
    JOB_DESCRIPTION = "job_description"
    COVER_LETTER = "cover_letter"


class DocumentFormat(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    PLAIN_TEXT = "plain_text"


@dataclass(frozen=True, slots=True)
class Page:
    document_id: str
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class Span:
    """Stable citation unit: offsets into the normalised page text."""

    id: str
    document_id: str
    page_number: int
    start_offset: int
    end_offset: int
    text: str

    def __post_init__(self) -> None:
        if self.start_offset < 0 or self.end_offset < self.start_offset:
            raise ValueError("span offsets must satisfy 0 <= start <= end")


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    kind: DocumentKind
    filename: str
    format: DocumentFormat
    page_count: int
    character_count: int
    parsed_at: datetime


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    document: Document
    pages: tuple[Page, ...]
    spans: tuple[Span, ...]


@dataclass(frozen=True, slots=True)
class Evidence:
    """Wire-shaped span resolution result."""

    document_id: str
    page: int
    paragraph: str
    highlight: str
