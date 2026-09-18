"""DOCX text extraction — paragraphs become page text (single logical page)."""

from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from career_assistant.application.intake.errors import IntakeError, IntakeErrorCode
from career_assistant.domain.normalisation import normalise_text


def extract_docx_pages(data: bytes) -> list[str]:
    try:
        document = Document(BytesIO(data))
    except (PackageNotFoundError, ValueError, KeyError, OSError) as exc:
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_UNREADABLE,
            "Document has no extractable content.",
        ) from exc

    paragraphs = [p.text for p in document.paragraphs if p.text is not None]
    joined = "\n\n".join(paragraphs)
    normalised = normalise_text(joined)
    return [normalised] if normalised else [""]
