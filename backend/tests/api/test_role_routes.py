"""Phase 11.8 — role create/list/get and job poll (minimal)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.main import create_app


def test_create_role_requires_cv() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/roles",
        json={
            "title": "Analytics Engineer",
            "company": "Acme",
            "description": "Need dbt and SQL experience.",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "cv_required"


def test_create_role_returns_202_with_job() -> None:
    client = TestClient(create_app())
    client.post(
        "/api/cv",
        json={"text": "Owned dbt models in production.", "filename": "cv.txt"},
    )

    response = client.post(
        "/api/roles",
        json={
            "title": "Analytics Engineer",
            "company": "Acme",
            "description": "Need dbt and SQL experience for warehouses.",
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["role"]["title"] == "Analytics Engineer"
    assert body["role"]["company"] == "Acme"
    assert body["role"]["status"] == "analysing"
    assert body["role"]["fitScore"] == 0
    assert body["jobId"]

    listed = client.get("/api/roles")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == body["role"]["id"]

    fetched = client.get(f"/api/roles/{body['role']['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["company"] == "Acme"

    job = client.get(f"/api/jobs/{body['jobId']}")
    assert job.status_code == 200
    assert job.json()["id"] == body["jobId"]
    assert job.json()["state"] in {"queued", "running", "succeeded", "failed"}


def test_get_unknown_role_returns_404() -> None:
    client = TestClient(create_app())
    response = client.get("/api/roles/00000000-0000-4000-8000-000000000099")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "role_not_found"
