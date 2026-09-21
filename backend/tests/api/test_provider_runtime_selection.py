"""Phase 13A.4 — persisted provider choice drives actual completion work."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from pydantic import SecretStr
from tests.support.scripted_transport import ScriptedTransport

from career_assistant.adapters.providers.http_transport import HttpResponse
from career_assistant.main import create_app
from career_assistant.settings import ProviderSettings

_CV = """Experience
Senior Analytics Engineer — Acme — 2022-01 — Present
- Owned dbt models in production for the warehouse.
"""

_JD = """Requirements
- Must have production dbt experience
"""

_QUESTION = "How did I describe my warehouse work?"


def _openai_settings() -> ProviderSettings:
    return ProviderSettings(
        completion_provider="hermetic",
        embedding_provider="hermetic",
        allow_hosted_providers=True,
        openai_api_key=SecretStr("sk-test-never-leave-the-fixture"),
        openai_completion_model="gpt-4o-mini",
        openai_embedding_model="text-embedding-3-small",
    )


def _scripted_openai_answer(text: str) -> ScriptedTransport:
    payload = {
        "choices": [
            {
                "message": {"content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 8, "completion_tokens": 6},
    }
    return ScriptedTransport(
        {"/chat/completions": HttpResponse(200, json.dumps(payload).encode(), {})}
    )


def test_open_question_calls_the_selected_scripted_provider() -> None:
    transport = _scripted_openai_answer("The CV cites owned dbt models in production.")
    app = create_app(providers=_openai_settings())
    app.state.http_transport = transport
    client = TestClient(app)
    assert client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"}).status_code == 201
    role_id = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    ).json()["role"]["id"]

    chosen = client.put(
        "/api/settings/providers",
        json={
            "answerProviderId": "openai",
            "answerModel": "gpt-4o-mini",
            "indexProviderId": "hermetic",
            "indexModel": "lexical-hash-v1",
            "acknowledgedEgress": True,
        },
    )
    assert chosen.status_code == 200

    asked = client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json={
            "content": _QUESTION,
            "roleId": role_id,
            "clientRequestId": "cr-selected-provider-1",
        },
    )
    assert asked.status_code == 200
    body = asked.json()
    assert body["provider"] == "openai"
    assert body["model"] == "gpt-4o-mini"
    assert body["leftMachine"] is True
    assert transport.calls
    assert any("/chat/completions" in url for _method, url in transport.calls)
