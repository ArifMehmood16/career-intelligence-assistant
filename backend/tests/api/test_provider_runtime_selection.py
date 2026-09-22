"""Phase 13A.4 — persisted provider choice drives actual completion work."""

from __future__ import annotations

import json
from collections.abc import Mapping

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
    """Return span-id classifications/assignments from the extractor prompt."""
    import re

    span_block = re.compile(
        r"SPAN (\S+)\nUNTRUSTED_SPAN_BEGIN\n(.*?)\nUNTRUSTED_SPAN_END",
        re.DOTALL,
    )

    def _payload_for(json_body: Mapping[str, object] | None) -> dict[str, object]:
        messages = []
        if isinstance(json_body, Mapping):
            raw = json_body.get("messages")
            if isinstance(raw, list):
                messages = raw
        user = ""
        for message in messages:
            if isinstance(message, dict) and message.get("role") == "user":
                user = str(message.get("content") or "")
        blocks = list(span_block.findall(user))
        if "UNTRUSTED_CV" in user or "UNTRUSTED_COVER_LETTER" in user:
            last_role: str | None = None
            assignments: list[dict[str, object]] = []
            for span, text in blocks:
                if re.search(r"\b(?:19|20)\d{2}\b", text) and "—" in text:
                    last_role = span
                    assignments.append({"spanId": span, "kind": "role_heading"})
                elif last_role is not None and text.lstrip().startswith("-"):
                    assignments.append(
                        {
                            "spanId": span,
                            "kind": "experience",
                            "roleSpanId": last_role,
                        }
                    )
                else:
                    assignments.append({"spanId": span, "kind": "narrative"})
            content: dict[str, object] = {"assignments": assignments}
        else:
            classifications: list[dict[str, object]] = []
            for span, text in blocks:
                if "must have" in text.lower() or "dbt" in text.lower():
                    kind = "requirement"
                    must_have = True
                    competency = "dbt"
                else:
                    kind = "non_requirement"
                    must_have = False
                    competency = "general"
                classifications.append(
                    {
                        "spanId": span,
                        "item_type": kind,
                        "must_have": must_have,
                        "competency": competency,
                    }
                )
            content = {"classifications": classifications}
        return {
            "choices": [
                {
                    "message": {"content": json.dumps(content)},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 20},
        }

    class _ExtractionTransport(ScriptedTransport):
        def request(
            self,
            method: str,
            url: str,
            *,
            headers: Mapping[str, str] | None = None,
            json_body: Mapping[str, object] | None = None,
            timeout_seconds: float,
        ) -> HttpResponse:
            del headers, timeout_seconds
            self.calls.append((method, url))
            if "/chat/completions" in url:
                return HttpResponse(
                    200, json.dumps(_payload_for(json_body)).encode(), {}
                )
            raise AssertionError(f"no recorded response for {method} {url}")

    return _ExtractionTransport(responses={})


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


def test_bullet_phrasing_calls_the_selected_scripted_provider() -> None:
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
    role_id = created_role.json()["role"]["id"]
    requirements = client.get(f"/api/roles/{role_id}/requirements").json()
    requirement_id = next(
        item["id"] for item in requirements if "dbt" in item["text"].lower()
    )
    calls_after_analysis = len(transport.calls)

    drafted = client.post(
        f"/api/roles/{role_id}/bullets",
        json={"requirementId": requirement_id},
    )
    assert drafted.status_code == 200
    provenance = drafted.json()["provenance"]
    assert provenance["provider"] == "openai"
    assert provenance["model"] == "gpt-4o-mini"
    assert provenance["leftMachine"] is True
    assert len(transport.calls) > calls_after_analysis


def test_open_question_records_accounting_without_document_text() -> None:
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
            "clientRequestId": "cr-accounting-1",
        },
    )
    assert asked.status_code == 200
    records = app.state.call_accountant.records
    assert records
    entry = records[-1]
    assert entry.provider_id == "openai"
    assert entry.model_tag == "gpt-4o-mini"
    assert entry.left_machine is True
    dumped = str(records)
    assert "warehouse" not in dumped
    assert "dbt" not in dumped
