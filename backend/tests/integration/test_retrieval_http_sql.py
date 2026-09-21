"""Phase 13A.5 — production HTTP retrieval and span resolution against PostgreSQL."""

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

_LETTER = """Dear Hiring Manager,

I wrote about Kubernetes operators in my cover letter.

Kind regards
"""

_CUDA_LETTER = """Experience
Senior GPU Engineer — Lab — 2020-01 — Present
- Built CUDA kernels in production.
"""


def _sql_app(
    session_factory: sessionmaker[Session],
) -> tuple[TestClient, SqlAnalysisWorker, SqlSupportingDocumentStore]:
    def uow_factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    cv_store = SqlCvStore(uow_factory)
    supporting = SqlSupportingDocumentStore(uow_factory=uow_factory, cv_store=cv_store)
    worker = SqlAnalysisWorker(uow_factory)
    client = TestClient(
        create_app(
            cv_store=cv_store,
            role_store=SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory),
            supporting_store=supporting,
            conversation_store=SqlConversationStore(uow_factory),
            provider_choice_store=SqlProviderSettingsStore(uow_factory),
        )
    )
    return client, worker, supporting


def _span_containing(
    supporting: SqlSupportingDocumentStore, workspace_id: str, needle: str
) -> str:
    lowered = needle.lower()
    for span in supporting.spans_for_workspace(workspace_id):
        if lowered in span.text.lower():
            return span.id
    raise AssertionError(f"no supporting span contains {needle!r}")


def test_sql_get_span_opens_cover_letter_and_rejects_other_workspace(
    session_factory: sessionmaker[Session],
) -> None:
    app_client, _worker, supporting = _sql_app(session_factory)
    created = app_client.post(
        "/api/cover-letters",
        json={"text": _LETTER, "filename": "letter.txt"},
    )
    assert created.status_code == 201
    workspace = app_client.cookies[WORKSPACE_COOKIE]
    span_id = _span_containing(supporting, workspace, "Kubernetes")

    opened = app_client.get(f"/api/spans/{span_id}")
    assert opened.status_code == 200
    body = opened.json()
    assert body["spanId"] == span_id
    assert body["documentId"] == created.json()["id"]
    assert "kubernetes" in body["highlight"].lower()

    stranger, _, _ = _sql_app(session_factory)
    denied = stranger.get(f"/api/spans/{span_id}")
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "span_not_found"
    assert stranger.cookies[WORKSPACE_COOKIE] != workspace


def test_sql_get_span_opens_job_description_after_analysis(
    session_factory: sessionmaker[Session],
) -> None:
    client, worker, _supporting = _sql_app(session_factory)
    assert (
        client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"}).status_code
        == 201
    )
    created = client.post(
        "/api/roles",
        json={
            "title": "Backend",
            "company": "Acme",
            "description": (
                "Requirements\n- Must have FastAPI experience in production.\n"
            ),
        },
    )
    assert created.status_code == 202
    worker.drain()
    role_id = created.json()["role"]["id"]
    workspace = client.cookies[WORKSPACE_COOKIE]
    jd_spans = client.app.state.role_store.job_description_spans(workspace)
    role_spans = [item for item in jd_spans if item.role_id == role_id]
    assert role_spans
    span_id = role_spans[0].span.id

    opened = client.get(f"/api/spans/{span_id}")
    assert opened.status_code == 200
    body = opened.json()
    assert body["spanId"] == span_id
    excerpt = f"{body['highlight']} {body['paragraph']}".lower()
    assert "fastapi" in excerpt


def test_sql_open_question_cites_cover_letter_and_same_role_jd(
    session_factory: sessionmaker[Session],
) -> None:
    client, worker, supporting = _sql_app(session_factory)
    assert (
        client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"}).status_code
        == 201
    )
    letter = client.post(
        "/api/cover-letters",
        json={"text": _LETTER, "filename": "letter.txt"},
    )
    assert letter.status_code == 201
    workspace = client.cookies[WORKSPACE_COOKIE]
    cl_span = _span_containing(supporting, workspace, "Kubernetes")

    role_a = client.post(
        "/api/roles",
        json={
            "title": "GPU",
            "company": "Acme",
            "description": "Requirements\n- Need CUDA for GPU kernels.\n",
        },
    ).json()["role"]["id"]
    role_b = client.post(
        "/api/roles",
        json={
            "title": "Robotics",
            "company": "Acme",
            "description": "Requirements\n- Need ROS2 navigation stack.\n",
        },
    ).json()["role"]["id"]
    worker.drain()

    asked_letter = client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json={
            "content": "What did I write in my cover letter about Kubernetes?",
            "clientRequestId": "cr-sql-cover-1",
        },
    )
    assert asked_letter.status_code == 200
    assert cl_span in {item["id"] for item in asked_letter.json()["citations"]}

    jd_spans = client.app.state.role_store.job_description_spans(workspace)
    span_a = next(item.span.id for item in jd_spans if item.role_id == role_a)
    span_b = next(item.span.id for item in jd_spans if item.role_id == role_b)
    asked_role = client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json={
            "content": "What does this role say about CUDA?",
            "roleId": role_a,
            "clientRequestId": "cr-sql-role-1",
        },
    )
    assert asked_role.status_code == 200
    citation_ids = {item["id"] for item in asked_role.json()["citations"]}
    assert span_a in citation_ids
    assert span_b not in citation_ids


def test_sql_cover_letter_cannot_meet_a_role_requirement(
    session_factory: sessionmaker[Session],
) -> None:
    client, worker, _supporting = _sql_app(session_factory)
    assert (
        client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"}).status_code
        == 201
    )
    letter = client.post(
        "/api/cover-letters",
        json={"text": _CUDA_LETTER, "filename": "letter.txt"},
    )
    assert letter.status_code == 201
    created = client.post(
        "/api/roles",
        json={
            "title": "GPU",
            "company": "Acme",
            "description": (
                "Requirements\n"
                "- Must have production dbt experience\n"
                "- Must have CUDA experience\n"
            ),
        },
    )
    assert created.status_code == 202
    worker.drain()
    role_id = created.json()["role"]["id"]
    rows = client.get(f"/api/roles/{role_id}/requirements").json()
    dbt = next(row for row in rows if "dbt" in row["text"].lower())
    cuda = next(row for row in rows if "cuda" in row["text"].lower())
    assert dbt["status"] == "met"
    assert cuda["status"] == "missing"
    assert cuda["evidence"] is None
