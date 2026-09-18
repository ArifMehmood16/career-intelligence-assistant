"""Phase 3 intake behaviours — written to fail until parsers and pipeline exist."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from career_assistant.application.intake.admission import (
    AdmissionLimits,
    admit_pasted_text,
    admit_upload,
)
from career_assistant.application.intake.errors import IntakeError, IntakeErrorCode
from career_assistant.application.intake.resolve_span import (
    SpanNotFoundError,
    resolve_span,
)
from career_assistant.domain.documents import (
    DocumentFormat,
    DocumentKind,
    Page,
    Span,
)
from career_assistant.domain.normalisation import normalise_text, paragraph_spans

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_CV = ROOT / "sample-data" / "fixtures" / "resumes" / "cv-strong-match.txt"


# --- 3.6 Normalisation -------------------------------------------------------


def test_normalisation_expands_ligatures_and_bullets() -> None:
    raw = "ef\ufb01cient\n\u2022 owned dbt"
    out = normalise_text(raw)
    assert "efficient" in out
    assert "- owned dbt" in out


def test_normalisation_joins_hyphenated_line_breaks() -> None:
    raw = "transfor-\nmation pipeline"
    assert normalise_text(raw) == "transformation pipeline"


def test_paragraph_span_offsets_round_trip_exact_slices() -> None:
    page = normalise_text("First paragraph.\n\nSecond paragraph with detail.")
    parts = paragraph_spans(page)
    assert len(parts) == 2
    for start, end, text in parts:
        assert page[start:end] == text


# --- 3.5 Admission -----------------------------------------------------------


def test_admission_rejects_oversized_upload() -> None:
    limits = AdmissionLimits(max_upload_bytes=16)
    with pytest.raises(IntakeError) as err:
        admit_upload(b"x" * 20, filename="big.txt", limits=limits)
    assert err.value.code == IntakeErrorCode.DOCUMENT_TOO_LARGE


def test_admission_rejects_unsupported_magic_despite_pdf_extension() -> None:
    with pytest.raises(IntakeError) as err:
        admit_upload(b"\xff\xd8\xff\xe0not-a-pdf", filename="fake.pdf")
    assert err.value.code == IntakeErrorCode.DOCUMENT_UNSUPPORTED


def test_admission_accepts_plain_text_by_content() -> None:
    admitted = admit_upload(
        b"SYNTHETIC FIXTURE\n\n- SQL",
        filename="notes.bin",
        declared_media_type="application/octet-stream",
    )
    assert admitted.format == DocumentFormat.PLAIN_TEXT


def test_admission_accepts_pasted_text() -> None:
    admitted = admit_pasted_text("Role requirements:\n- Python")
    assert admitted.format == DocumentFormat.PLAIN_TEXT
    assert b"Python" in admitted.data


# --- 3.7 Span resolution -----------------------------------------------------


def test_resolve_span_highlight_is_substring_of_paragraph() -> None:
    page_text = "Intro line.\n\nOwned dbt models in production.\n\nClosing."
    page = Page(document_id="doc-1", page_number=1, text=page_text)
    start = page_text.index("Owned dbt")
    end = start + len("Owned dbt models in production.")
    span = Span(
        id="span-1",
        document_id="doc-1",
        page_number=1,
        start_offset=start,
        end_offset=end,
        text=page_text[start:end],
    )
    evidence = resolve_span(span, (page,))
    assert evidence.highlight in evidence.paragraph
    assert evidence.highlight == span.text
    assert evidence.page == 1


def test_resolve_span_unknown_id_raises() -> None:
    page = Page(document_id="doc-1", page_number=1, text="hello")
    span = Span(
        id="missing",
        document_id="doc-1",
        page_number=2,
        start_offset=0,
        end_offset=5,
        text="hello",
    )
    with pytest.raises(SpanNotFoundError):
        resolve_span(span, (page,))


# --- 3.1–3.4 Parse pipeline (must fail until implemented) --------------------


def test_plain_text_fixture_parses_to_spans_with_round_trip() -> None:
    from career_assistant.parsing.pipeline import parse_document

    raw = FIXTURE_CV.read_text(encoding="utf-8")
    parsed = parse_document(
        raw.encode("utf-8"),
        filename="cv-strong-match.txt",
        kind=DocumentKind.CV,
        document_id="cv-test",
        parsed_at=datetime(2026, 9, 18, tzinfo=UTC),
    )
    assert parsed.document.format == DocumentFormat.PLAIN_TEXT
    assert parsed.document.page_count >= 1
    assert parsed.spans
    by_id = {span.id: span for span in parsed.spans}
    sample = parsed.spans[0]
    evidence = resolve_span(sample, parsed.pages)
    assert evidence.highlight == sample.text
    assert by_id[sample.id].text == evidence.highlight


def test_pdf_bytes_parse_preserve_offsets() -> None:
    from tests.support.document_bytes import make_pdf_bytes

    from career_assistant.parsing.pipeline import parse_document

    pdf = make_pdf_bytes(["SYNTHETIC FIXTURE\n\nOwned dbt models in production."])
    parsed = parse_document(
        pdf,
        filename="cv.pdf",
        kind=DocumentKind.CV,
        document_id="cv-pdf",
        parsed_at=datetime(2026, 9, 18, tzinfo=UTC),
    )
    assert parsed.document.format == DocumentFormat.PDF
    assert any("dbt" in span.text for span in parsed.spans)
    sample = next(span for span in parsed.spans if "dbt" in span.text)
    page = next(p for p in parsed.pages if p.page_number == sample.page_number)
    assert page.text[sample.start_offset : sample.end_offset] == sample.text


def test_docx_bytes_parse_preserve_offsets() -> None:
    from tests.support.document_bytes import make_docx_bytes

    from career_assistant.parsing.pipeline import parse_document

    docx = make_docx_bytes(["SYNTHETIC FIXTURE", "Owned dbt models in production."])
    parsed = parse_document(
        docx,
        filename="cv.docx",
        kind=DocumentKind.CV,
        document_id="cv-docx",
        parsed_at=datetime(2026, 9, 18, tzinfo=UTC),
    )
    assert parsed.document.format == DocumentFormat.DOCX
    sample = next(span for span in parsed.spans if "dbt" in span.text)
    page = parsed.pages[0]
    assert page.text[sample.start_offset : sample.end_offset] == sample.text


def test_encrypted_pdf_is_unreadable() -> None:
    from tests.support.document_bytes import make_encrypted_pdf_bytes

    from career_assistant.parsing.pipeline import parse_document

    with pytest.raises(IntakeError) as err:
        parse_document(
            make_encrypted_pdf_bytes(),
            filename="secret.pdf",
            kind=DocumentKind.CV,
            document_id="cv-enc",
            parsed_at=datetime(2026, 9, 18, tzinfo=UTC),
        )
    assert err.value.code == IntakeErrorCode.DOCUMENT_UNREADABLE


def test_empty_pdf_is_unreadable() -> None:
    from tests.support.document_bytes import make_pdf_bytes

    from career_assistant.parsing.pipeline import parse_document

    with pytest.raises(IntakeError) as err:
        parse_document(
            make_pdf_bytes([""]),
            filename="blank.pdf",
            kind=DocumentKind.CV,
            document_id="cv-blank",
            parsed_at=datetime(2026, 9, 18, tzinfo=UTC),
        )
    assert err.value.code == IntakeErrorCode.DOCUMENT_UNREADABLE
