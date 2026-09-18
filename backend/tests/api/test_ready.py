"""Phase 11.5 — readiness reports database, migrations and provider state."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from career_assistant.main import create_app


@dataclass(frozen=True, slots=True)
class _FakeReadiness:
    database: str = "ok"
    migrations: str = "current"
    completion_provider: str = "hermetic"
    embedding_provider: str = "hermetic"
    hosted_egress: bool = False


def test_ready_returns_camel_case_status_payload() -> None:
    client = TestClient(create_app(readiness=_FakeReadiness()))

    response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {
        "database": "ok",
        "migrations": "current",
        "completionProvider": "hermetic",
        "embeddingProvider": "hermetic",
        "hostedEgress": False,
    }


def test_ready_returns_503_when_database_unavailable() -> None:
    client = TestClient(create_app(readiness=_FakeReadiness(database="unavailable")))

    response = client.get("/api/ready")

    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
    assert response.json()["migrations"] == "current"


def test_ready_response_model_serialises_aliases() -> None:
    from career_assistant.api.schemas import ReadyResponse

    payload = ReadyResponse(
        database="ok",
        migrations="current",
        completion_provider="hermetic",
        embedding_provider="hermetic",
        hosted_egress=False,
    )
    assert payload.model_dump(by_alias=True)["completionProvider"] == "hermetic"
    assert payload.model_dump(by_alias=True)["hostedEgress"] is False
