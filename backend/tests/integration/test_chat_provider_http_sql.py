"""Phase 13A.2 — chat and provider choice survive a fresh app process (Postgres)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.analysis_worker import SqlAnalysisWorker
from career_assistant.adapters.persistence.conversation_store import (
    SqlConversationStore,
)
from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.provider_settings_store import (
    SqlProviderSettingsStore,
)
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.supporting_store import (
    SqlSupportingDocumentStore,
)
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.api.deps import WORKSPACE_COOKIE
from career_assistant.main import create_app

pytestmark = pytest.mark.integration

_CV = """Experience
Senior Analytics Engineer — Acme — 2022-01 — Present
- Owned dbt models in production for the warehouse.
"""

_JD = """Requirements
- Must have production dbt experience
"""

_QUESTION = "What evidence do I have for the production dbt requirement?"


def _sql_app(
    session_factory: sessionmaker[Session],
) -> tuple[TestClient, SqlAnalysisWorker]:
    def uow_factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    cv_store = SqlCvStore(uow_factory)
    worker = SqlAnalysisWorker(uow_factory)
    return (
        TestClient(
            create_app(
                cv_store=cv_store,
                role_store=SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory),
                supporting_store=SqlSupportingDocumentStore(
                    uow_factory=uow_factory, cv_store=cv_store
                ),
                conversation_store=SqlConversationStore(uow_factory),
                provider_choice_store=SqlProviderSettingsStore(uow_factory),
            )
        ),
        worker,
    )


def _copy_workspace(source: TestClient, dest: TestClient) -> str:
    workspace = source.cookies[WORKSPACE_COOKIE]
    dest.cookies.set(WORKSPACE_COOKIE, workspace)
    return workspace


def _seed_role(client: TestClient, worker: SqlAnalysisWorker) -> str:
    created_cv = client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    assert created_cv.status_code == 201
    created_role = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    assert created_role.status_code == 202
    worker.drain()
    return created_role.json()["role"]["id"]


def test_messages_survive_fresh_app_process(
    session_factory: sessionmaker[Session],
) -> None:
    first, worker = _sql_app(session_factory)
    role_id = _seed_role(first, worker)
    asked = first.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json={
            "content": _QUESTION,
            "roleId": role_id,
            "clientRequestId": "cr-survive-1",
        },
    )
    assert asked.status_code == 200
    answer = asked.json()
    answer_id = answer["id"]
    assert answer["citations"]

    second, _ = _sql_app(session_factory)
    _copy_workspace(first, second)
    history = second.get("/api/messages")
    assert history.status_code == 200
    body = history.json()
    assert body[0]["author"] == "user"
    assert body[0]["content"] == _QUESTION
    assistant = body[-1]
    assert assistant["id"] == answer_id
    assert assistant["author"] == "assistant"
    assert assistant["citations"] == answer["citations"]
    assert assistant["provider"]
    assert assistant["model"]


def test_message_idempotent_retry_survives_fresh_app(
    session_factory: sessionmaker[Session],
) -> None:
    first, worker = _sql_app(session_factory)
    role_id = _seed_role(first, worker)
    payload = {
        "content": "How well do I fit this role?",
        "roleId": role_id,
        "clientRequestId": "cr-retry-1",
    }
    first_ask = first.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json=payload,
    )
    assert first_ask.status_code == 200
    answer_id = first_ask.json()["id"]

    second, _ = _sql_app(session_factory)
    _copy_workspace(first, second)
    retry = second.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json=payload,
    )
    assert retry.status_code == 200
    assert retry.json()["id"] == answer_id
    history = second.get("/api/messages").json()
    assert len([m for m in history if m["author"] == "assistant"]) == 1


def test_delete_messages_is_durable_and_workspace_scoped(
    session_factory: sessionmaker[Session],
) -> None:
    first, worker = _sql_app(session_factory)
    role_a = _seed_role(first, worker)
    assert (
        first.post(
            "/api/messages",
            headers={"Accept": "application/json"},
            json={
                "content": "How well do I fit this role?",
                "roleId": role_a,
                "clientRequestId": "cr-del-a",
            },
        ).status_code
        == 200
    )
    workspace_a = first.cookies[WORKSPACE_COOKIE]

    other, other_worker = _sql_app(session_factory)
    role_b = _seed_role(other, other_worker)
    assert (
        other.post(
            "/api/messages",
            headers={"Accept": "application/json"},
            json={
                "content": "How well do I fit this role?",
                "roleId": role_b,
                "clientRequestId": "cr-del-b",
            },
        ).status_code
        == 200
    )
    workspace_b = other.cookies[WORKSPACE_COOKIE]
    assert workspace_a != workspace_b

    deleted = first.delete("/api/messages")
    assert deleted.status_code == 204

    restarted, _ = _sql_app(session_factory)
    restarted.cookies.set(WORKSPACE_COOKIE, workspace_a)
    assert restarted.get("/api/messages").json() == []

    restarted.cookies.set(WORKSPACE_COOKIE, workspace_b)
    remaining = restarted.get("/api/messages").json()
    assert remaining
    assert remaining[-1]["author"] == "assistant"


def test_provider_choice_survives_fresh_app_including_model_tags(
    session_factory: sessionmaker[Session],
) -> None:
    first, _worker = _sql_app(session_factory)
    put = first.put(
        "/api/settings/providers",
        json={
            "answerProviderId": "hermetic",
            "answerModel": "rules-v1",
            "indexProviderId": "hermetic",
            "indexModel": "lexical-hash-v1",
            "acknowledgedEgress": False,
        },
    )
    assert put.status_code == 200
    expected = put.json()

    second, _ = _sql_app(session_factory)
    _copy_workspace(first, second)
    got = second.get("/api/settings/providers")
    assert got.status_code == 200
    assert got.json() == expected
    assert got.json()["answerModel"] == "rules-v1"
    assert got.json()["indexModel"] == "lexical-hash-v1"
