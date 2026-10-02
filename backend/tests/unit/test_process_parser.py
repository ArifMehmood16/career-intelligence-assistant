"""Binary parsing works in spawned CPU workers with safe, serializable failures."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from tests.support.document_bytes import make_docx_bytes, make_pdf_bytes

from career_assistant.application.intake.admission import AdmissionLimits
from career_assistant.application.intake.errors import IntakeError, IntakeErrorCode
from career_assistant.application.ports.intake import UploadDocument
from career_assistant.domain.documents import DocumentKind
from career_assistant.parsing.process_pool import ProcessUploadParser


def _upload(data: bytes) -> UploadDocument:
    return UploadDocument(data, "synthetic", DocumentKind.CV, None, AdmissionLimits())


def test_binary_documents_are_parsed_concurrently_in_spawned_processes() -> None:
    parser = ProcessUploadParser(workers=2)
    uploads = (
        _upload(make_pdf_bytes(["Synthetic Python engineer"])),
        _upload(make_docx_bytes(["Synthetic SQL engineer"])),
    )
    try:
        with ThreadPoolExecutor(max_workers=2) as threads:
            parsed = list(threads.map(parser.parse, uploads))
        assert parsed[0].pages[0].text == "Synthetic Python engineer"
        assert parsed[1].pages[0].text == "Synthetic SQL engineer"
    finally:
        parser.close()


def test_process_parser_preserves_intake_failure_codes() -> None:
    parser = ProcessUploadParser(workers=1)
    upload = replace(
        _upload(make_pdf_bytes(["Synthetic first", "Synthetic second"])),
        limits=AdmissionLimits(max_document_pages=1),
    )
    try:
        with pytest.raises(IntakeError) as error:
            parser.parse(upload)
        assert error.value.code is IntakeErrorCode.DOCUMENT_TOO_LARGE
    finally:
        parser.close()


def test_plain_text_avoids_process_startup() -> None:
    parser = ProcessUploadParser(workers=1)
    try:
        assert parser.parse(_upload(b"Synthetic profile")).pages[0].text == (
            "Synthetic profile"
        )
    finally:
        parser.close()
