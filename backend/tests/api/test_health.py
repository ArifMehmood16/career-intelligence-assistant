"""Liveness is the first behaviour: the process answers before it can do anything."""

from fastapi.testclient import TestClient

from career_assistant.main import create_app


def test_health_reports_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_does_not_touch_dependencies() -> None:
    """Liveness must answer with no database and no provider configured."""
    client = TestClient(create_app())

    assert client.get("/api/health").status_code == 200
