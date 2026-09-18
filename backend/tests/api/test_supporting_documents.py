"""Phase 11.12 — supporting cover letters and document download."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.main import create_app

_LETTER = """Dear Hiring Manager,

I am applying for the Analytics Engineer role. I owned dbt models in production.

Kind regards
"""


def test_cover_letter_upload_list_delete_and_download() -> None:
    client = TestClient(create_app())

    empty = client.get("/api/cover-letters")
    assert empty.status_code == 200
    assert empty.json() == []

    created = client.post(
        "/api/cover-letters",
        json={"text": _LETTER, "filename": "previous-letter.txt"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["kind"] == "cover_letter"
    assert body["filename"] == "previous-letter.txt"
    assert body["mediaType"] == "text/plain"
    assert body["byteLength"] == len(_LETTER.encode("utf-8"))
    assert body["pageCount"] >= 1
    assert "parsedAt" in body and "createdAt" in body
    assert "path" not in body and "originalBytes" not in body
    doc_id = body["id"]

    listed = client.get("/api/cover-letters")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == doc_id

    downloaded = client.get(f"/api/documents/{doc_id}/download")
    assert downloaded.status_code == 200
    assert downloaded.content == _LETTER.encode("utf-8")
    assert downloaded.headers["content-type"].startswith("text/plain")
    disposition = downloaded.headers.get("content-disposition", "")
    assert "attachment" in disposition.lower()
    assert "previous-letter.txt" in disposition
    assert "/" not in disposition.split("filename=")[-1].strip('"')

    deleted = client.delete(f"/api/cover-letters/{doc_id}")
    assert deleted.status_code == 204
    assert client.get("/api/cover-letters").json() == []
    missing = client.get(f"/api/documents/{doc_id}/download")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "cover_letter_not_found"


def test_delete_unknown_cover_letter_is_404() -> None:
    client = TestClient(create_app())
    response = client.delete("/api/cover-letters/00000000-0000-4000-8000-000000000099")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "cover_letter_not_found"


def test_cv_download_is_workspace_scoped_and_safe() -> None:
    client = TestClient(create_app())
    uploaded = client.post(
        "/api/cv",
        json={"text": "Owned dbt models in production.", "filename": "cv.txt"},
    )
    assert uploaded.status_code == 201
    cv_id = uploaded.json()["id"]

    downloaded = client.get(f"/api/documents/{cv_id}/download")
    assert downloaded.status_code == 200
    assert b"Owned dbt" in downloaded.content
    assert "attachment" in downloaded.headers.get("content-disposition", "").lower()
    assert "path" not in downloaded.text.lower()
