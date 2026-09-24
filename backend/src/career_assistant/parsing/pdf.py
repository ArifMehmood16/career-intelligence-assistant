"""PDF text extraction with per-page strings."""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from career_assistant.application.intake.errors import IntakeError, IntakeErrorCode
from career_assistant.domain.normalisation import normalise_text
from career_assistant.parsing.reflow import reflow_wrapped_lines


def extract_pdf_pages(data: bytes) -> list[str]:
    try:
        reader = PdfReader(BytesIO(data))
    except PdfReadError as exc:
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_UNREADABLE,
            "Document has no extractable content.",
        ) from exc

    if reader.is_encrypted:
        # Try empty password; otherwise treat as unreadable (no credential prompt).
        try:
            unlocked = bool(reader.decrypt(""))
        except Exception:
            unlocked = False
        if not unlocked:
            raise IntakeError(
                IntakeErrorCode.DOCUMENT_UNREADABLE,
                "Document has no extractable content.",
            )

    pages: list[str] = []
    try:
        for page in reader.pages:
            raw = page.extract_text() or ""
            pages.append(reflow_wrapped_lines(normalise_text(raw)))
    except FileNotDecryptedError as exc:
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_UNREADABLE,
            "Document has no extractable content.",
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive parser boundary
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_UNREADABLE,
            "Document has no extractable content.",
        ) from exc

    return pages or [""]
