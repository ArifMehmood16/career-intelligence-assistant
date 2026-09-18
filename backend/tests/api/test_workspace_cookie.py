"""Phase 11.2 — workspace cookie issuance and reuse on API requests."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from career_assistant.main import create_app


def test_first_request_issues_httponly_samesite_workspace_cookie() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    raw = response.headers.get("set-cookie", "")
    assert "workspace=" in raw
    assert "HttpOnly" in raw
    assert "SameSite=lax" in raw.lower()
    workspace_id = response.cookies["workspace"]
    uuid.UUID(workspace_id)


def test_existing_workspace_cookie_is_reused() -> None:
    client = TestClient(create_app())
    existing = str(uuid.uuid4())
    client.cookies.set("workspace", existing)

    response = client.get("/api/health")

    assert response.cookies.get("workspace") == existing
    # Re-issuing the same value is fine; changing it is not.
    set_cookie = response.headers.get("set-cookie", "")
    if set_cookie:
        assert existing in set_cookie


def test_invalid_workspace_cookie_is_replaced() -> None:
    client = TestClient(create_app())
    client.cookies.set("workspace", "not-a-uuid")

    response = client.get("/api/health")

    assert response.status_code == 200
    replacement = response.cookies["workspace"]
    assert replacement != "not-a-uuid"
    uuid.UUID(replacement)


def test_workspace_dependency_returns_cookie_value() -> None:
    from career_assistant.api.deps import resolve_workspace_id

    existing = str(uuid.uuid4())
    assert resolve_workspace_id(existing) == existing
    issued = resolve_workspace_id(None)
    uuid.UUID(issued)
    replaced = resolve_workspace_id("bad")
    uuid.UUID(replaced)
    assert replaced != "bad"
