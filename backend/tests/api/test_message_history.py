"""Phase 11.13 — message history, hard delete, JSON/SSE same answer id."""

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
"""

_EVENT = re.compile(
    r"event:\s*(\w+)\s*\ndata:\s*(\{.*?\})\s*\n",
    re.DOTALL,
)


def _role(client: TestClient) -> str:
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


def test_get_messages_returns_persisted_history_in_order() -> None:
    client = TestClient(create_app())
    role_id = _role(client)

    assert client.get("/api/messages").json() == []

    asked = client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json={
            "content": "How well do I fit this role?",
            "roleId": role_id,
            "clientRequestId": "cr-hist-1",
        },
    )
    assert asked.status_code == 200
    answer_id = asked.json()["id"]

    history = client.get("/api/messages")
    assert history.status_code == 200
    body = history.json()
    assert len(body) >= 2
    assert body[0]["author"] == "user"
    assert body[0]["kind"] == "question"
    assert body[-1]["author"] == "assistant"
    assert body[-1]["id"] == answer_id
    assert "leftMachine" in body[-1]
    assert body[-1]["provider"]


def test_json_and_sse_share_stored_answer_id_on_retry() -> None:
    client = TestClient(create_app())
    role_id = _role(client)
    payload = {
        "content": "How well do I fit this role?",
        "roleId": role_id,
        "clientRequestId": "cr-same-id",
    }

    first = client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json=payload,
    )
    assert first.status_code == 200
    answer_id = first.json()["id"]

    second = client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json=payload,
    )
    assert second.status_code == 200
    assert second.json()["id"] == answer_id

    with client.stream(
        "POST",
        "/api/messages",
        headers={"Accept": "text/event-stream"},
        json=payload,
    ) as streamed:
        assert streamed.status_code == 200
        text = "".join(streamed.iter_text())
    meta = next(
        json.loads(match.group(2))
        for match in _EVENT.finditer(text)
        if match.group(1) == "meta"
    )
    assert meta["messageId"] == answer_id


def test_delete_messages_hard_deletes_history() -> None:
    client = TestClient(create_app())
    role_id = _role(client)
    client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json={
            "content": "How well do I fit this role?",
            "roleId": role_id,
            "clientRequestId": "cr-del-1",
        },
    )
    assert client.get("/api/messages").json()

    deleted = client.delete("/api/messages")
    assert deleted.status_code == 204
    assert client.get("/api/messages").json() == []
