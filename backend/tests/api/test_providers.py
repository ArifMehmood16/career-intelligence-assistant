"""Phase 11.7 — provider catalogue and workspace provider choice."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.main import create_app
from career_assistant.settings import ProviderSettings


def _client(
    *,
    providers: ProviderSettings | None = None,
) -> TestClient:
    return TestClient(create_app(providers=providers))


def test_list_providers_includes_hermetic_as_available() -> None:
    response = _client().get("/api/providers")

    assert response.status_code == 200
    body = response.json()
    hermetic = next(p for p in body if p["id"] == "hermetic")
    assert hermetic["kind"] == "local"
    assert hermetic["available"] is True
    assert hermetic["unavailableReason"] is None
    assert hermetic["supports"] == {"completion": True, "embedding": True}
    assert "capabilities" in hermetic


def test_hosted_provider_unavailable_when_egress_closed() -> None:
    settings = ProviderSettings(
        allow_hosted_providers=False,
        openai_api_key=None,
    )
    response = _client(providers=settings).get("/api/providers")

    openai = next(p for p in response.json() if p["id"] == "openai")
    assert openai["kind"] == "hosted"
    assert openai["available"] is False
    assert openai["unavailableReason"]


def test_get_provider_choice_defaults_from_settings() -> None:
    settings = ProviderSettings(
        completion_provider="hermetic",
        embedding_provider="hermetic",
        ollama_completion_model="llama3.2",
        ollama_embedding_model="nomic-embed-text",
    )
    response = _client(providers=settings).get("/api/settings/providers")

    assert response.status_code == 200
    assert response.json() == {
        "answerProviderId": "hermetic",
        "answerModel": "rules-v1",
        "indexProviderId": "hermetic",
        "indexModel": "hash-v1",
    }


def test_put_hosted_without_ack_returns_egress_not_acknowledged() -> None:
    settings = ProviderSettings(
        allow_hosted_providers=True,
        openai_api_key="sk-test-secret-key-never-return",
        openai_completion_model="gpt-4o-mini",
        openai_embedding_model="text-embedding-3-small",
    )
    response = _client(providers=settings).put(
        "/api/settings/providers",
        json={
            "answerProviderId": "openai",
            "answerModel": "gpt-4o-mini",
            "indexProviderId": "openai",
            "indexModel": "text-embedding-3-small",
            "acknowledgedEgress": False,
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "egress_not_acknowledged"


def test_put_hosted_while_gate_closed_returns_egress_not_permitted() -> None:
    settings = ProviderSettings(allow_hosted_providers=False)
    response = _client(providers=settings).put(
        "/api/settings/providers",
        json={
            "answerProviderId": "openai",
            "answerModel": "gpt-4o-mini",
            "indexProviderId": "hermetic",
            "indexModel": "hash-v1",
            "acknowledgedEgress": True,
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "egress_not_permitted"


def test_put_local_choice_persists_for_workspace() -> None:
    client = _client()
    put = client.put(
        "/api/settings/providers",
        json={
            "answerProviderId": "hermetic",
            "answerModel": "rules-v1",
            "indexProviderId": "hermetic",
            "indexModel": "hash-v1",
            "acknowledgedEgress": False,
        },
    )
    assert put.status_code == 200
    assert put.json()["answerProviderId"] == "hermetic"

    got = client.get("/api/settings/providers")
    assert got.status_code == 200
    assert got.json()["answerProviderId"] == "hermetic"


def test_provider_responses_never_include_api_key_material() -> None:
    secret = "sk-super-secret-should-never-leak"
    settings = ProviderSettings(
        allow_hosted_providers=True,
        openai_api_key=secret,
    )
    client = _client(providers=settings)

    listed = client.get("/api/providers")
    choice = client.get("/api/settings/providers")
    updated = client.put(
        "/api/settings/providers",
        json={
            "answerProviderId": "openai",
            "answerModel": "gpt-4o-mini",
            "indexProviderId": "hermetic",
            "indexModel": "hash-v1",
            "acknowledgedEgress": True,
        },
    )

    for response in (listed, choice, updated):
        assert secret not in response.text
        assert "sk-super" not in response.text
