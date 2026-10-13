"""Phase 13B — operational logs on stderr, never document text or secrets."""

from __future__ import annotations

import io
import logging

from fastapi.testclient import TestClient

from career_assistant.application.observability.memory import InMemoryAuditRecorder
from career_assistant.logconfig import configure_logging, format_fields
from career_assistant.main import create_app

_PLANTED_CV = "PLANTED_CV_PHRASE_MUST_NOT_APPEAR_IN_LOGS_9f3c2a"
_PLANTED_JD = "PLANTED_JD_PHRASE_MUST_NOT_APPEAR_IN_LOGS_7b1e4d"
_PLANTED_KEY = "sk-planted-secret-key-value-for-redaction"


def _request_lines(buffer: io.StringIO) -> list[str]:
    return [line for line in buffer.getvalue().splitlines() if " request " in line]


def test_a_successful_get_logs_at_debug_with_one_correlation_id() -> None:
    buffer = io.StringIO()
    configure_logging(force=True, stream=buffer, level=logging.DEBUG)
    client = TestClient(create_app())

    response = client.get(
        "/api/health", headers={"X-Correlation-Id": "corr-log-test-1"}
    )
    configure_logging(force=True)

    assert response.status_code == 200
    (line,) = _request_lines(buffer)
    assert " DEBUG career_assistant.http request method=GET path=/api/health" in line
    assert "status=200" in line
    assert line.count("correlation_id=corr-log-test-1") == 1


def test_polling_gets_are_quiet_at_info_but_failures_are_not() -> None:
    buffer = io.StringIO()
    configure_logging(force=True, stream=buffer, level=logging.INFO)
    client = TestClient(create_app())

    client.get("/api/health")
    missing = client.get("/api/roles/00000000-0000-0000-0000-000000000000")
    configure_logging(force=True)

    assert missing.status_code == 404
    (line,) = _request_lines(buffer)
    assert " INFO career_assistant.http request method=GET" in line
    assert "status=404" in line


def test_cv_upload_logs_operation_without_document_text(
    caplog: logging.LogCaptureFixture,
) -> None:
    configure_logging(force=True)
    caplog.set_level(logging.INFO, logger="career_assistant")
    client = TestClient(create_app())

    response = client.post(
        "/api/cv",
        files={
            "file": (
                "cv.txt",
                f"Owned dbt models. {_PLANTED_CV}\n".encode(),
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    assert "cv.uploaded" in caplog.text
    assert "document_id=" in caplog.text
    assert _PLANTED_CV not in caplog.text
    assert "Owned dbt models" not in caplog.text


def test_format_fields_refuses_long_or_multiline_values() -> None:
    rendered = format_fields(
        document_id="doc-1",
        leaked="line1\n" + _PLANTED_CV,
        blob="x" * 500,
    )
    assert "document_id=doc-1" in rendered
    assert _PLANTED_CV not in rendered
    assert "x" * 50 not in rendered
    assert "multiline" in rendered or "len=500" in rendered


def test_redacting_filter_masks_planted_api_key(
    caplog: logging.LogCaptureFixture,
) -> None:
    configure_logging(force=True)
    caplog.set_level(logging.INFO, logger="career_assistant")
    log = logging.getLogger("career_assistant.security")
    log.info("provider_constructed key=%s", _PLANTED_KEY)

    assert _PLANTED_KEY not in caplog.text
    assert "redacted" in caplog.text.lower()


def test_role_create_logs_operation_without_job_text(
    caplog: logging.LogCaptureFixture,
) -> None:
    configure_logging(force=True)
    caplog.set_level(logging.INFO, logger="career_assistant")
    client = TestClient(create_app())
    client.post(
        "/api/cv",
        files={"file": ("cv.txt", b"Owned dbt models in production.\n", "text/plain")},
    )

    response = client.post(
        "/api/roles",
        json={
            "title": "Analytics Engineer",
            "company": "Acme",
            "description": f"Must have dbt. {_PLANTED_JD}\n",
        },
    )

    assert response.status_code == 202
    assert "role.created" in caplog.text
    assert "job_id=" in caplog.text
    assert _PLANTED_JD not in caplog.text


def test_validation_error_logs_code_not_request_body(
    caplog: logging.LogCaptureFixture,
) -> None:
    configure_logging(force=True)
    caplog.set_level(logging.INFO, logger="career_assistant")
    client = TestClient(create_app())

    response = client.post(
        "/api/roles",
        json={"title": _PLANTED_JD, "description": _PLANTED_JD},
    )

    assert response.status_code in {409, 422}
    assert "http.error" in caplog.text
    assert "code=" in caplog.text
    assert _PLANTED_JD not in caplog.text


def test_log_failure_includes_module_and_function_site(
    caplog: logging.LogCaptureFixture,
) -> None:
    from career_assistant.logconfig import log_failure

    configure_logging(force=True)
    caplog.set_level(logging.ERROR, logger="career_assistant")
    log = logging.getLogger("career_assistant.test_site")

    def _emit_failure() -> None:
        log_failure(
            log,
            "test.failed",
            code="unit",
            input="spans_supplied=3,stage=extracting_claims",
        )

    _emit_failure()

    assert "test.failed" in caplog.text
    assert "site=" in caplog.text
    assert "_emit_failure" in caplog.text
    assert "input=spans_supplied=3" in caplog.text
    assert _PLANTED_CV not in caplog.text


def test_health_request_records_http_envelope_without_secrets() -> None:
    configure_logging(force=True)
    client = TestClient(create_app())

    response = client.get(
        "/api/health",
        headers={
            "X-Correlation-Id": "corr-log-test-1",
            "Authorization": f"Bearer {_PLANTED_KEY}",
        },
    )

    assert response.status_code == 200
    recorder = client.app.state.audit_recorder
    assert isinstance(recorder, InMemoryAuditRecorder)
    envelope = recorder.http[-1]
    assert envelope.method == "GET"
    assert envelope.path == "/api/health"
    assert envelope.status == 200
    assert envelope.correlation_id == "corr-log-test-1"
    dumped = repr(envelope)
    assert _PLANTED_KEY not in dumped
    assert "Authorization" not in dumped
    assert not hasattr(envelope, "body")


def test_validation_error_records_error_code_not_request_body() -> None:
    configure_logging(force=True)
    client = TestClient(create_app())

    response = client.post(
        "/api/roles",
        json={"title": _PLANTED_JD, "description": _PLANTED_JD},
    )

    assert response.status_code in {409, 422}
    recorder = client.app.state.audit_recorder
    assert isinstance(recorder, InMemoryAuditRecorder)
    envelope = recorder.http[-1]
    assert envelope.error_code is not None
    assert envelope.status in {409, 422}
    assert _PLANTED_JD not in repr(envelope)
    assert _PLANTED_JD not in (envelope.error_code or "")
