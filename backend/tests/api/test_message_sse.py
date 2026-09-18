"""Phase 11.9 — POST /api/messages SSE event sequence."""

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


def _parse_sse(body: str) -> list[tuple[str, dict[str, object]]]:
    events: list[tuple[str, dict[str, object]]] = []
    for match in _EVENT.finditer(body):
        events.append((match.group(1), json.loads(match.group(2))))
    return events


def test_post_messages_streams_documented_sse_sequence() -> None:
    client = TestClient(create_app())
    assert (
        client.post(
            "/api/cv",
            json={"text": _CV, "filename": "cv.txt"},
        ).status_code
        == 201
    )
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    assert created.status_code == 202
    role_id = created.json()["role"]["id"]

    with client.stream(
        "POST",
        "/api/messages",
        headers={"Accept": "text/event-stream"},
        json={
            "content": "What gaps should I close first?",
            "roleId": role_id,
            "clientRequestId": "cr-sse-1",
        },
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        payload = "".join(response.iter_text())

    events = _parse_sse(payload)
    types = [name for name, _ in events]
    assert types[0] == "meta"
    assert "token" in types
    assert types[-2] == "citations"
    assert types[-1] == "done"

    meta = events[0][1]
    assert meta["intent"] == "gaps"
    assert meta["provider"]
    assert meta["questionId"]
    assert meta["messageId"]

    tokens = "".join(
        str(data["text"]) for name, data in events if name == "token" and "text" in data
    )
    assert tokens

    done = events[-1][1]
    assert done["kind"] in {"answer", "insufficient"}
