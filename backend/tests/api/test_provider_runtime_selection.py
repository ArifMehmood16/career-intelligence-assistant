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
    created = client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    assert created.status_code == 201
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


def test_rejected_hosted_choice_makes_no_network_attempt() -> None:
    transport = _scripted_openai_answer("must not be used")
    app = create_app(providers=_openai_settings())
    app.state.http_transport = transport
    client = TestClient(app)
    created = client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    assert created.status_code == 201
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

    app.state.providers.allow_hosted_providers = False
    asked = client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json={
            "content": _QUESTION,
            "roleId": role_id,
            "clientRequestId": "cr-rejected-hosted-1",
        },
    )
    assert asked.status_code == 403
    assert asked.json()["error"]["code"] == "egress_not_permitted"
    assert transport.calls == []


def _scripted_openai_extraction() -> ScriptedTransport:
    claim = "Owned dbt models in production for the warehouse."
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "requirements": [
                                {
                                    "text": "Must have production dbt experience",
                                    "must_have": True,
                                }
                            ],
                            "claims": [{"text": claim}],
                        }
                    )
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 20},
    }
    return ScriptedTransport(
        {"/chat/completions": HttpResponse(200, json.dumps(payload).encode(), {})}
    )


def test_requirement_extraction_calls_the_selected_scripted_provider() -> None:
    transport = _scripted_openai_extraction()
    app = create_app(providers=_openai_settings())
    app.state.http_transport = transport
    client = TestClient(app)
    created = client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    assert created.status_code == 201
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

    created_role = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    assert created_role.status_code == 202
    assert transport.calls
    assert any("/chat/completions" in url for _method, url in transport.calls)
    role_id = created_role.json()["role"]["id"]
    requirements = client.get(f"/api/roles/{role_id}/requirements")
    assert requirements.status_code == 200
    assert requirements.json()
