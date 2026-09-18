"""Phase 11.8 — GET /api/spans/{id} returns Evidence with spanId."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.main import create_app


def test_get_span_returns_evidence_for_uploaded_cv() -> None:
    client = TestClient(create_app())
    client.post(
        "/api/cv",
        json={"text": "Owned dbt models in production.", "filename": "cv.txt"},
    )
    # Resolve span id from the in-memory store via a second call path:
    # upload stores spans; list is not yet public, so fetch through app state.
    store = client.app.state.cv_store
    workspace_id = client.cookies.get("workspace")
    stored = store.get_active(workspace_id)
    assert stored is not None
    span_id = stored.spans[0].id

    response = client.get(f"/api/spans/{span_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["spanId"] == span_id
    assert body["documentId"] == stored.view.id
    assert body["page"] == 1
    assert "dbt" in body["paragraph"].lower() or "dbt" in body["highlight"].lower()
    assert body["highlight"]
    assert body["highlight"] in body["paragraph"]


def test_get_unknown_span_returns_span_not_found() -> None:
    client = TestClient(create_app())
    response = client.get("/api/spans/00000000-0000-4000-8000-000000000099")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "span_not_found"
