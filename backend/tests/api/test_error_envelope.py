"""Phase 11.4 — safe error envelope mapped from the contract code table."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from career_assistant.api.errors import AppError, install_exception_handlers
from career_assistant.api.middleware import CorrelationIdMiddleware
from career_assistant.api.schemas import ApiModel, ErrorBody, ErrorEnvelope


class _ProbeBody(ApiModel):
    page_count: int


def _probe_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    install_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise AppError("role_not_found", "No role with that id.", status_code=404)

    @app.get("/crash")
    def crash() -> None:
        raise RuntimeError("secret path /tmp/leak and provider payload xyz")

    @app.post("/validate")
    def validate(body: _ProbeBody) -> _ProbeBody:
        return body

    return app


def test_app_error_returns_contract_envelope_with_correlation_id() -> None:
    client = TestClient(_probe_app())

    response = client.get("/boom", headers={"X-Correlation-Id": "corr-boom-1"})

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "role_not_found",
            "message": "No role with that id.",
            "correlationId": "corr-boom-1",
        }
    }
    assert response.headers["X-Correlation-Id"] == "corr-boom-1"


def test_unhandled_exception_maps_to_internal_error_without_leak() -> None:
    client = TestClient(_probe_app(), raise_server_exceptions=False)

    response = client.get("/crash", headers={"X-Correlation-Id": "corr-crash-1"})

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["correlationId"] == "corr-crash-1"
    message = body["error"]["message"]
    assert "/tmp/" not in message
    assert "provider payload" not in message
    assert "Traceback" not in message
    assert "RuntimeError" not in message


def test_validation_failure_uses_validation_failed_code() -> None:
    client = TestClient(_probe_app())

    response = client.post(
        "/validate",
        json={"pageCount": "not-an-int"},
        headers={"X-Correlation-Id": "corr-val-1"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_failed"
    assert body["error"]["correlationId"] == "corr-val-1"
    assert "message" in body["error"]


def test_error_envelope_model_is_camel_case() -> None:
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code="internal_error",
            message="Something went wrong.",
            correlation_id="abc",
        )
    )
    assert envelope.model_dump(by_alias=True) == {
        "error": {
            "code": "internal_error",
            "message": "Something went wrong.",
            "correlationId": "abc",
        }
    }
