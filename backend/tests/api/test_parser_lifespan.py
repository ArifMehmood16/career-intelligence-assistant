"""Application shutdown releases parser workers with or without an analysis worker."""

import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.support.document_bytes import make_pdf_bytes
from tests.support.process_parse_probe import assert_worker_stopped, reporting_parse

from career_assistant.application.intake.admission import AdmissionLimits
from career_assistant.application.ports.intake import UploadDocument
from career_assistant.domain.documents import DocumentKind
from career_assistant.main import create_app
from career_assistant.parsing import process_pool


class WaitingWorker:
    """A lifespan collaborator that needs neither SQL nor provider access."""

    def __init__(self) -> None:
        self.started = threading.Event()
        self.stopped = threading.Event()

    def run_forever(self, *, stop: threading.Event) -> None:
        self.started.set()
        if stop.wait(timeout=20):
            self.stopped.set()


@pytest.mark.parametrize("with_worker", [False, True])
def test_lifespan_closes_real_parser_workers(
    with_worker: bool, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    marker = tmp_path / "synthetic-worker-pid"
    monkeypatch.setattr(process_pool, "_parse", reporting_parse)
    app = create_app()
    worker = WaitingWorker()
    if with_worker:
        app.state.analysis_worker = worker
    upload = UploadDocument(
        make_pdf_bytes(["Synthetic lifespan"]),
        str(marker),
        DocumentKind.CV,
        None,
        AdmissionLimits(),
    )
    try:
        with TestClient(app) as client:
            assert client.get("/api/health").status_code == 200
            if with_worker:
                assert worker.started.wait(timeout=2)
            parsed = app.state.upload_parser.parse(upload)
            assert parsed.pages[0].text == "Synthetic lifespan"
        assert_worker_stopped(marker)
        if with_worker:
            assert worker.stopped.is_set()
    finally:
        app.state.upload_parser.close()
