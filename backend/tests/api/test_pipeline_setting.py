"""PLAN 18.10 — a workspace chooses the v1 or v2 matching pipeline."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.main import create_app

ROUTE = "/api/settings/pipeline"


def test_pipeline_defaults_to_v1() -> None:
    response = TestClient(create_app()).get(ROUTE)

    assert response.status_code == 200
    assert response.json() == {"pipelineVersion": "v1"}


def test_put_pipeline_switches_the_workspace_to_v2() -> None:
    client = TestClient(create_app())

    put = client.put(ROUTE, json={"pipelineVersion": "v2"})

    assert put.status_code == 200
    assert put.json() == {"pipelineVersion": "v2"}
    assert client.get(ROUTE).json() == {"pipelineVersion": "v2"}


def test_put_rejects_an_unknown_pipeline() -> None:
    response = TestClient(create_app()).put(ROUTE, json={"pipelineVersion": "v3"})

    assert response.status_code == 422
