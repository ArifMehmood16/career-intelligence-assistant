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


def _cover_letter_span_id(client: TestClient) -> str:
    workspace_id = client.cookies["workspace"]
    letters = client.app.state.supporting_store._letters[workspace_id]
    stored = next(iter(letters.values()))
    assert stored.spans
    return stored.spans[0].id


def test_get_span_returns_evidence_for_uploaded_cover_letter() -> None:
    client = TestClient(create_app())
    created = client.post(
        "/api/cover-letters",
        json={
            "text": "I wrote about Kubernetes operators in my cover letter.",
            "filename": "letter.txt",
        },
    )
    assert created.status_code == 201
    span_id = _cover_letter_span_id(client)

    response = client.get(f"/api/spans/{span_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["spanId"] == span_id
    assert body["documentId"] == created.json()["id"]
    assert "kubernetes" in body["highlight"].lower()
    assert body["highlight"] in body["paragraph"]


def test_get_span_returns_evidence_for_role_job_description() -> None:
    client = TestClient(create_app())
    uploaded = client.post(
        "/api/cv",
        json={"text": "Python engineer with FastAPI.", "filename": "cv.txt"},
    )
    assert uploaded.status_code == 201
    created = client.post(
        "/api/roles",
        json={
            "title": "Backend",
            "company": "Acme",
            "description": (
                "Requirements\n- Must have FastAPI experience in production.\n"
            ),
        },
    )
    assert created.status_code == 202
    role_id = created.json()["role"]["id"]
    workspace_id = client.cookies["workspace"]
    bundle = client.app.state.role_store.analyses[workspace_id][role_id]
    assert bundle.jd_spans
    span_id = bundle.jd_spans[0].id

    response = client.get(f"/api/spans/{span_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["spanId"] == span_id
    assert body["documentId"] == bundle.jd_document_id
    assert body["highlight"] in body["paragraph"]
    assert "fastapi" in body["highlight"].lower() or "fastapi" in body[
        "paragraph"
    ].lower()


def test_get_span_rejects_cross_workspace_citation() -> None:
    app = create_app()
    owner = TestClient(app)
    stranger = TestClient(app)
    created = owner.post(
        "/api/cover-letters",
        json={
            "text": "I wrote about Kubernetes operators in my cover letter.",
            "filename": "letter.txt",
        },
    )
    assert created.status_code == 201
    workspace_id = owner.cookies["workspace"]
    stored = next(
        iter(owner.app.state.supporting_store._letters[workspace_id].values())
    )
    span_id = stored.spans[0].id

    response = stranger.get(f"/api/spans/{span_id}")

    assert owner.cookies["workspace"] != stranger.cookies["workspace"]
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "span_not_found"
