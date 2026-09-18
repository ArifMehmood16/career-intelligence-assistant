"""Admission policy — sniff content, enforce caps, never trust extensions alone."""

from __future__ import annotations

from dataclasses import dataclass

from career_assistant.application.intake.errors import IntakeError, IntakeErrorCode
from career_assistant.domain.documents import DocumentFormat

# Magic sniffing — minimal signatures, no extension trust.
_PDF_MAGIC = b"%PDF"
_ZIP_MAGIC = b"PK\x03\x04"
_DOCX_NAME = b"word/"


@dataclass(frozen=True, slots=True)
class AdmissionLimits:
    max_upload_bytes: int = 10_485_760
    max_document_pages: int = 40
    max_document_chars: int = 400_000


@dataclass(frozen=True, slots=True)
class AdmittedBytes:
    data: bytes
    format: DocumentFormat
    filename: str


def admit_upload(
    data: bytes,
    *,
    filename: str,
    declared_media_type: str | None = None,
    limits: AdmissionLimits | None = None,
) -> AdmittedBytes:
    policy = limits or AdmissionLimits()
    if len(data) > policy.max_upload_bytes:
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_TOO_LARGE,
            "Document exceeds the configured upload size limit.",
        )
    if not data:
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_UNREADABLE,
            "Document has no extractable content.",
        )

    detected = _sniff_format(data, declared_media_type=declared_media_type)
    if detected is None:
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_UNSUPPORTED,
            "Only PDF, DOCX and plain text documents are accepted.",
        )
    return AdmittedBytes(data=data, format=detected, filename=filename or "upload")


def admit_pasted_text(
    text: str,
    *,
    filename: str = "pasted.txt",
    limits: AdmissionLimits | None = None,
) -> AdmittedBytes:
    policy = limits or AdmissionLimits()
    encoded = text.encode("utf-8")
    if len(encoded) > policy.max_upload_bytes:
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_TOO_LARGE,
            "Document exceeds the configured upload size limit.",
        )
    if not text.strip():
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_UNREADABLE,
            "Document has no extractable content.",
        )
    if len(text) > policy.max_document_chars:
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_TOO_LARGE,
            "Document exceeds the configured character limit.",
        )
    return AdmittedBytes(
        data=encoded,
        format=DocumentFormat.PLAIN_TEXT,
        filename=filename or "pasted.txt",
    )


def enforce_parsed_limits(
    *,
    page_count: int,
    character_count: int,
    limits: AdmissionLimits | None = None,
) -> None:
    policy = limits or AdmissionLimits()
    if page_count > policy.max_document_pages:
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_TOO_LARGE,
            "Document exceeds the configured page limit.",
        )
    if character_count > policy.max_document_chars:
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_TOO_LARGE,
            "Document exceeds the configured character limit.",
        )
    if character_count == 0:
        raise IntakeError(
            IntakeErrorCode.DOCUMENT_UNREADABLE,
            "Document has no extractable content.",
        )


def _sniff_format(
    data: bytes, *, declared_media_type: str | None
) -> DocumentFormat | None:
    head = data[:8]
    if head.startswith(_PDF_MAGIC):
        return DocumentFormat.PDF
    if head.startswith(_ZIP_MAGIC) and _DOCX_NAME in data[:4096]:
        return DocumentFormat.DOCX
    # OOXML may place [Content_Types].xml first; still a ZIP.
    if head.startswith(_ZIP_MAGIC) and b"[Content_Types].xml" in data[:8192]:
        if b"word/" in data[:65536]:
            return DocumentFormat.DOCX
    media = (declared_media_type or "").lower()
    if media.startswith("text/plain") and _looks_like_text(data):
        return DocumentFormat.PLAIN_TEXT
    if _looks_like_text(data):
        return DocumentFormat.PLAIN_TEXT
    return None


def _looks_like_text(data: bytes) -> bool:
    sample = data[:4096]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return False
    # Reject high binary ratio
    non_text = sum(1 for b in sample if b < 9 or (13 < b < 32))
    return non_text / max(len(sample), 1) < 0.05
