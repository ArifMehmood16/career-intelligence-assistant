"""A workspace cannot switch back to the retired analysis architecture."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.main import create_app


def test_pipeline_selector_is_removed() -> None:
    client = TestClient(create_app())
    assert client.get("/api/settings/pipeline").status_code == 404
    assert (
        client.put("/api/settings/pipeline", json={"pipelineVersion": "v1"}).status_code
        == 404
    )
