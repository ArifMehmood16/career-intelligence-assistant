"""Phase 11.10 — answers and drafts carry provider, model, leftMachine."""

from __future__ import annotations

import json
import re

from fastapi.testclient import TestClient

from career_assistant.main import create_app

_CV = """Experience
Senior Analytics Engineer — Acme — 2022-01 — Present
- Owned dbt models in production for the warehouse.
"""

_JD = """Requirements
- Must have production dbt experience
Nice to have
- Looker dashboards
"""

_EVENT = re.compile(
    r"event:\s*(\w+)\s*\ndata:\s*(\{.*?\})\s*\n",
    re.DOTALL,
)


def _setup_role(client: TestClient) -> str:
    assert (
        client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"}).status_code
        == 201
    )
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    assert created.status_code == 202
    return created.json()["role"]["id"]


def _assert_provenance(payload: dict[str, object]) -> None:
    assert "provider" in payload and isinstance(payload["provider"], str)
    assert "model" in payload  # may be null for template path
    assert "leftMachine" in payload and isinstance(payload["leftMachine"], bool)


def test_sse_meta_carries_provider_model_and_left_machine() -> None:
    client = TestClient(create_app())
    role_id = _setup_role(client)

    with client.stream(
        "POST",
        "/api/messages",
        headers={"Accept": "text/event-stream"},
        json={
            "content": "How well do I fit this role?",
            "roleId": role_id,
            "clientRequestId": "cr-prov-sse",
        },
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    events = [
        (match.group(1), json.loads(match.group(2))) for match in _EVENT.finditer(body)
    ]
    meta = next(data for name, data in events if name == "meta")
    _assert_provenance(
        {
            "provider": meta["provider"],
            "model": meta["model"],
            "leftMachine": meta["leftMachine"],
        }
    )
    assert meta["leftMachine"] is False


def test_json_answer_carries_provider_model_and_left_machine() -> None:
    client = TestClient(create_app())
    role_id = _setup_role(client)

    response = client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json={
            "content": "How well do I fit this role?",
            "roleId": role_id,
            "clientRequestId": "cr-prov-json",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["author"] == "assistant"
    _assert_provenance(
        {
            "provider": body["provider"],
            "model": body["model"],
            "leftMachine": body["leftMachine"],
        }
    )
    assert body["leftMachine"] is False


def test_draft_and_interview_pack_responses_carry_provenance() -> None:
    client = TestClient(create_app())
    role_id = _setup_role(client)

    pack = client.get(f"/api/roles/{role_id}/interview-pack")
    assert pack.status_code == 200
    _assert_provenance(pack.json()["provenance"])

    requirements = client.get(f"/api/roles/{role_id}/requirements")
    assert requirements.status_code == 200
    requirement_id = requirements.json()[0]["id"]

    bullets = client.post(
        f"/api/roles/{role_id}/bullets",
        json={"requirementId": requirement_id},
    )
    assert bullets.status_code == 200
    _assert_provenance(bullets.json()["provenance"])

    letter = client.post(
        f"/api/roles/{role_id}/cover-letter",
        json={"tone": "plain", "includeGapLine": False},
    )
    assert letter.status_code in {200, 409}
    if letter.status_code == 200:
        _assert_provenance(letter.json()["provenance"])
