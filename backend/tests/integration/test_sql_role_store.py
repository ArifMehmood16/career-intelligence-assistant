"""Phase 11.8 — SqlRoleStore create/list/get/require_analysis over PostgreSQL."""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.analysis_worker import SqlAnalysisWorker
from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.documents.cv import (
    admission_limits_from,
    upload_pasted_cv,
)
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


def _uow_factory_for(
    session_factory: sessionmaker[Session],
) -> Callable[[], SqlUnitOfWork]:
    def factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    return factory


def test_sql_role_store_create_list_get_and_analysis(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = _uow_factory_for(session_factory)
    cv_store = SqlCvStore(uow_factory)
    role_store = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    worker = SqlAnalysisWorker(uow_factory)
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
    assert role.status == "analysing"
    assert job.state == "queued"
    worker.drain()
    role = role_store.get_role(workspace_id, role.id)
    assert role is not None
    assert role.status == "ready"
    assert role.company == "Acme"
    assert role.fit_score > 0
    finished = role_store.get_job(workspace_id, job.id)
    assert finished is not None
    assert finished.state == "succeeded"

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
    uow_factory = _uow_factory_for(session_factory)
    cv_store = SqlCvStore(uow_factory)
    role_store = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    worker = SqlAnalysisWorker(uow_factory)
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
    worker.drain()
    role = role_store.get_role(workspace_id, role.id)
    assert role is not None
    first_score = role.fit_score
    bundle_before = role_store.require_analysis(workspace_id, role.id)
    first_req_count = len(bundle_before.requirements)

    updated, new_job = role_store.reanalyse(workspace_id, role.id)
    assert updated.id == role.id
    assert updated.status == "analysing"
    assert new_job.state == "queued"
    assert new_job.id != first_job.id
    worker.drain()
    updated = role_store.get_role(workspace_id, role.id)
    assert updated is not None
    assert updated.status == "ready"
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
    uow_factory = _uow_factory_for(session_factory)
    cv_store = SqlCvStore(uow_factory)
    role_store = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    worker = SqlAnalysisWorker(uow_factory)
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
    worker.drain()

    reanalysed = client.post(f"/api/roles/{role_id}/reanalyse")
    assert reanalysed.status_code == 202
    assert reanalysed.json()["jobId"]
    worker.drain()
    assert client.get(f"/api/roles/{role_id}").json()["status"] == "ready"
    assert client.get(f"/api/roles/{role_id}/requirements").status_code == 200

    deleted = client.delete(f"/api/roles/{role_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/roles/{role_id}").status_code == 404


def test_role_http_routes_persist_via_sql_stores(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = _uow_factory_for(session_factory)
    cv_store = SqlCvStore(uow_factory)
    role_store = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    worker = SqlAnalysisWorker(uow_factory)
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
    assert body["role"]["status"] == "analysing"
    assert body["role"]["company"] == "Acme"
    role_id = body["role"]["id"]
    worker.drain()

    job = client.get(f"/api/jobs/{body['jobId']}")
    assert job.status_code == 200
    assert job.json()["state"] == "succeeded"
    assert client.get(f"/api/roles/{role_id}").json()["status"] == "ready"

    requirements = client.get(f"/api/roles/{role_id}/requirements")
    assert requirements.status_code == 200
    assert requirements.json()


def test_cover_letter_and_bullets_persist_across_store_instances(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = _uow_factory_for(session_factory)
    cv_store = SqlCvStore(uow_factory)
    role_store = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    worker = SqlAnalysisWorker(uow_factory)
    client = TestClient(create_app(cv_store=cv_store, role_store=role_store))

    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    role_id = client.post(
        "/api/roles",
        json={
            "title": "Analytics Engineer",
            "company": "Acme",
            "description": _JD,
        },
    ).json()["role"]["id"]
    worker.drain()

    requirements = client.get(f"/api/roles/{role_id}/requirements").json()
    requirement_id = requirements[0]["id"]

    bullets = client.post(
        f"/api/roles/{role_id}/bullets",
        json={"requirementId": requirement_id},
    )
    assert bullets.status_code == 200
    bullet_id = bullets.json()["id"]

    letter = client.post(
        f"/api/roles/{role_id}/cover-letter",
        json={"tone": "plain", "includeGapLine": False},
    )
    assert letter.status_code == 200, letter.text
    letter_id = letter.json()["id"]

    # Fresh store instance — only PostgreSQL may satisfy this.
    role_store_b = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    listed_letters = role_store_b.list_cover_letters(
        client.cookies["workspace"], role_id
    )
    assert len(listed_letters) == 1
    assert listed_letters[0].id == letter_id

    listed_bullets = role_store_b.list_bullet_drafts(
        client.cookies["workspace"], role_id
    )
    assert len(listed_bullets) == 1
    assert listed_bullets[0].id == bullet_id

    client_b = TestClient(create_app(cv_store=cv_store, role_store=role_store_b))
    client_b.cookies.set("workspace", client.cookies["workspace"])
    http_letters = client_b.get(f"/api/roles/{role_id}/cover-letters")
    assert http_letters.status_code == 200
    assert len(http_letters.json()) == 1
    assert http_letters.json()[0]["id"] == letter_id
    assert http_letters.json()[0]["provenance"]["leftMachine"] is False


def test_sql_role_store_persists_failed_template_fallback_verdict(
    session_factory: sessionmaker[Session],
) -> None:
    from types import SimpleNamespace

    from career_assistant.domain.groundedness import GroundednessVerdict

    uow_factory = _uow_factory_for(session_factory)
    cv_store = SqlCvStore(uow_factory)
    role_store = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    worker = SqlAnalysisWorker(uow_factory)
    client = TestClient(create_app(cv_store=cv_store, role_store=role_store))
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    role_id = client.post(
        "/api/roles",
        json={
            "title": "Analytics Engineer",
            "company": "Acme",
            "description": _JD,
        },
    ).json()["role"]["id"]
    worker.drain()
    workspace_id = client.cookies["workspace"]
    draft_id = str(uuid.uuid4())
    role_store.save_cover_letter(
        workspace_id,
        role_id,
        SimpleNamespace(
            id=draft_id,
            paragraphs=[{"text": "Template fallback.", "spanIds": []}],
            omitted_reason=None,
            provenance=SimpleNamespace(
                provider="hermetic",
                model="rules-v1",
                left_machine=False,
                grounded=False,
                fallback="template",
                generated_at="2026-09-21T12:00:00Z",
            ),
        ),
    )

    stored = role_store.list_cover_letters(workspace_id, role_id)
    assert stored[0].id == draft_id
    assert stored[0].groundedness is GroundednessVerdict.FAIL
    listed = client.get(f"/api/roles/{role_id}/cover-letters")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == draft_id
    assert listed.json()[0]["provenance"]["grounded"] is False
