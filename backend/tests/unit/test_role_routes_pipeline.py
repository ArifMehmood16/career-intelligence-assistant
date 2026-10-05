"""The hermetic store runs and reports the current single analysis."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.main import create_app


def test_a_hermetic_role_reports_the_current_pipeline() -> None:
    client = TestClient(create_app())
    client.post(
        "/api/cv",
        json={"text": "Experience\n- Owned dbt models.\n", "filename": "cv.txt"},
    )
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": "Requirements\n- dbt\n"},
    ).json()

    assert created["role"]["analysisPipeline"] == "v2"
    assert client.get("/api/roles").json()[0]["analysisPipeline"] == "v2"
