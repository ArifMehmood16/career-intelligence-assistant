"""Phase 11.8 — SqlRoleStore create/list/get/require_analysis over PostgreSQL."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.documents.cv import admission_limits_from, upload_pasted_cv
from career_assistant.main import create_app
from career_assistant.settings import LimitSettings

pytestmark = pytest.mark.integration

_CV = """Experience
Senior Analytics Engineer — Acme — 2022-01 — Present
- Owned dbt models in production for the warehouse.
- Built SQL pipelines on Snowflake.
"""

_JD = """Requirements
- Must have production dbt experience
- Must have SQL warehousing skills
Nice to have
- Looker dashboards
"""


def test_sql_role_store_create_list_get_and_analysis(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = lambda: SqlUnitOfWork(session_factory)
    cv_store = SqlCvStore(uow_factory)
    role_store = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    workspace_id = str(uuid.uuid4())

    upload_pasted_cv(
        cv_store,
        workspace_id=workspace_id,
        text=_CV,
        filename="cv.txt",
        limits=admission_limits_from(LimitSettings()),
    )

    role, job = role_store.create_role(
        workspace_id=workspace_id,
        title="Analytics Engineer",
        company="Acme",
        description=_JD,
    )
    assert role.status == "ready"
    assert role.company == "Acme"
    assert role.fit_score > 0
    assert job.state == "succeeded"

    listed = role_store.list_roles(workspace_id)
    assert len(listed) == 1
    assert listed[0].id == role.id

    fetched = role_store.get_role(workspace_id, role.id)
    assert fetched is not None
    assert fetched.title == "Analytics Engineer"

    bundle = role_store.require_analysis(workspace_id, role.id)
    assert bundle.requirements
    assert bundle.mappings
    assert bundle.explanation.score > 0


def test_sql_role_store_delete_and_reanalyse(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = lambda: SqlUnitOfWork(session_factory)
    cv_store = SqlCvStore(uow_factory)
    role_store = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    workspace_id = str(uuid.uuid4())

    upload_pasted_cv(
        cv_store,
        workspace_id=workspace_id,
        text=_CV,
        filename="cv.txt",
        limits=admission_limits_from(LimitSettings()),
    )
    role, first_job = role_store.create_role(
        workspace_id=workspace_id,
        title="Analytics Engineer",
        company="Acme",
        description=_JD,
    )
    first_score = role.fit_score
    first_req_count = len(role_store.require_analysis(workspace_id, role.id).requirements)

    updated, new_job = role_store.reanalyse(workspace_id, role.id)
    assert updated.id == role.id
    assert updated.status == "ready"
    assert new_job.state == "succeeded"
    assert new_job.id != first_job.id
    assert role_store.get_job(workspace_id, new_job.id) is not None
    bundle = role_store.require_analysis(workspace_id, role.id)
    assert len(bundle.requirements) == first_req_count
    assert updated.fit_score == first_score

    role_store.delete_role(workspace_id, role.id)
    assert role_store.get_role(workspace_id, role.id) is None
    assert role_store.list_roles(workspace_id) == ()


def test_role_http_delete_and_reanalyse_via_sql_stores(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = lambda: SqlUnitOfWork(session_factory)
    cv_store = SqlCvStore(uow_factory)
    role_store = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    client = TestClient(create_app(cv_store=cv_store, role_store=role_store))

    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    created = client.post(
        "/api/roles",
        json={
            "title": "Analytics Engineer",
            "company": "Acme",
            "description": _JD,
        },
    )
    assert created.status_code == 202
    role_id = created.json()["role"]["id"]

    reanalysed = client.post(f"/api/roles/{role_id}/reanalyse")
    assert reanalysed.status_code == 202
    assert reanalysed.json()["jobId"]
    assert client.get(f"/api/roles/{role_id}").json()["status"] == "ready"
    assert client.get(f"/api/roles/{role_id}/requirements").status_code == 200

    deleted = client.delete(f"/api/roles/{role_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/roles/{role_id}").status_code == 404


def test_role_http_routes_persist_via_sql_stores(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = lambda: SqlUnitOfWork(session_factory)
    cv_store = SqlCvStore(uow_factory)
    role_store = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    client = TestClient(create_app(cv_store=cv_store, role_store=role_store))

    assert (
        client.post(
            "/api/cv",
            json={"text": _CV, "filename": "cv.txt"},
        ).status_code
        == 201
    )

    created = client.post(
        "/api/roles",
        json={
            "title": "Analytics Engineer",
            "company": "Acme",
            "description": _JD,
        },
    )
    assert created.status_code == 202
    body = created.json()
    assert body["role"]["status"] == "ready"
    assert body["role"]["company"] == "Acme"
    role_id = body["role"]["id"]

    job = client.get(f"/api/jobs/{body['jobId']}")
    assert job.status_code == 200
    assert job.json()["state"] == "succeeded"

    requirements = client.get(f"/api/roles/{role_id}/requirements")
    assert requirements.status_code == 200
    assert requirements.json()
