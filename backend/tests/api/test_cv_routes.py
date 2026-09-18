"""Phase 11.8 — CV document routes (workspace-scoped)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.main import create_app
from career_assistant.settings import LimitSettings


def _client(*, limits: LimitSettings | None = None) -> TestClient:
    return TestClient(create_app(limits=limits))


def test_get_cv_returns_null_when_none_uploaded() -> None:
    response = _client().get("/api/cv")

    assert response.status_code == 200
    assert response.json() is None


def test_post_pasted_cv_returns_201_document() -> None:
    client = _client()

    response = client.post(
        "/api/cv",
        json={
            "text": "Owned dbt models in production.",
            "filename": "cv.txt",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "cv.txt"
    assert body["pageCount"] >= 1
    assert "id" in body
    assert "parsedAt" in body
    assert "reanalysis" in body
    assert body["reanalysis"]["jobIds"] == []


def test_get_cv_returns_uploaded_document() -> None:
    client = _client()
    created = client.post(
        "/api/cv",
        json={"text": "Led analytics engineering.", "filename": "resume.txt"},
    ).json()

    response = client.get("/api/cv")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["filename"] == "resume.txt"


def test_replace_cv_returns_new_document() -> None:
    client = _client()
    first = client.post(
        "/api/cv",
        json={"text": "First CV body.", "filename": "a.txt"},
    ).json()

    second = client.post(
        "/api/cv",
        json={"text": "Second CV body with more detail.", "filename": "b.txt"},
    )

    assert second.status_code == 201
    body = second.json()
    assert body["id"] != first["id"]
    assert body["filename"] == "b.txt"
    assert client.get("/api/cv").json()["id"] == body["id"]


def test_delete_cv_removes_active_document() -> None:
    client = _client()
    client.post("/api/cv", json={"text": "Temporary CV.", "filename": "tmp.txt"})

    deleted = client.delete("/api/cv")
    assert deleted.status_code == 204
    assert client.get("/api/cv").json() is None


def test_unreadable_paste_maps_to_document_unreadable() -> None:
    response = _client().post(
        "/api/cv",
        json={"text": "   ", "filename": "empty.txt"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "document_unreadable"


def test_oversized_paste_maps_to_document_too_large() -> None:
    limits = LimitSettings(max_upload_bytes=32, max_document_chars=32)
    response = _client(limits=limits).post(
        "/api/cv",
        json={"text": "x" * 64, "filename": "big.txt"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "document_too_large"
