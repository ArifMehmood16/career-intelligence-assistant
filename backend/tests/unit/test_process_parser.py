"""Binary parsing works in spawned CPU workers with safe, serializable failures."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
from tests.support.document_bytes import make_docx_bytes, make_pdf_bytes
from tests.support.process_parse_probe import (
    assert_worker_stopped,
    crashed_parse,
    reporting_parse,
    stalled_parse,
)

from career_assistant.application.intake.admission import AdmissionLimits
from career_assistant.application.intake.errors import IntakeError, IntakeErrorCode
from career_assistant.application.ports.intake import UploadDocument
from career_assistant.domain.documents import DocumentKind
from career_assistant.parsing import process_pool
from career_assistant.parsing.process_pool import ProcessUploadParser, _ParseResult


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


@pytest.mark.parametrize(
    "probe", [stalled_parse, crashed_parse], ids=["timeout", "crash"]
)
def test_failed_workers_exit_and_a_later_upload_gets_a_fresh_pool(
    probe: Callable[[UploadDocument], _ParseResult],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    marker = tmp_path / "synthetic-worker-pid"
    upload = replace(
        _upload(make_pdf_bytes(["Synthetic recovery"])), filename=str(marker)
    )
    parser = ProcessUploadParser(workers=1, timeout_seconds=5)
    original = process_pool._parse
    monkeypatch.setattr(process_pool, "_parse", probe)
    try:
        with pytest.raises(IntakeError) as error:
            parser.parse(upload)
        assert error.value.code is IntakeErrorCode.DOCUMENT_UNREADABLE
        assert_worker_stopped(marker)

        monkeypatch.setattr(process_pool, "_parse", original)
        assert parser.parse(upload).pages[0].text == "Synthetic recovery"
    finally:
        parser.close()


def test_close_terminates_workers_is_idempotent_and_allows_recreation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    marker = tmp_path / "synthetic-worker-pid"
    upload = replace(
        _upload(make_docx_bytes(["Synthetic close"])), filename=str(marker)
    )
    parser = ProcessUploadParser(workers=1)
    monkeypatch.setattr(process_pool, "_parse", reporting_parse)
    try:
        assert parser.parse(upload).pages[0].text == "Synthetic close"
        parser.close()
        assert_worker_stopped(marker)
        parser.close()
        assert parser.parse(upload).pages[0].text == "Synthetic close"
    finally:
        parser.close()
        assert_worker_stopped(marker)
