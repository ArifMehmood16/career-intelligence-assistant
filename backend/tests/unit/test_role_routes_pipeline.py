"""The in-memory store analyses on pipeline v1 and says so."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.main import create_app


def test_an_in_memory_role_reports_pipeline_v1() -> None:
    client = TestClient(create_app())
    client.post(
        "/api/cv",
        json={"text": "Experience\n- Owned dbt models.\n", "filename": "cv.txt"},
    )
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": "Requirements\n- dbt\n"},
    ).json()

    assert created["role"]["analysisPipeline"] == "v1"
    assert client.get("/api/roles").json()[0]["analysisPipeline"] == "v1"
