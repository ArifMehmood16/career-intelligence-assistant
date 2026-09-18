"""Phase 11.6 — correlation id on every request, echoed in responses."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.main import create_app


def test_response_echoes_incoming_correlation_id_header() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/api/health", headers={"X-Correlation-Id": "01TESTCORRELATION0001"}
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "01TESTCORRELATION0001"


def test_response_mints_correlation_id_when_absent() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    value = response.headers["X-Correlation-Id"]
    assert value
    assert len(value) >= 8


def test_resolve_correlation_id_prefers_request_header() -> None:
    from career_assistant.api.deps import resolve_correlation_id

    assert resolve_correlation_id("abc-123") == "abc-123"
    minted = resolve_correlation_id(None)
    assert minted
    assert minted != resolve_correlation_id(None)
