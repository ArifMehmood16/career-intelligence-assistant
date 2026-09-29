"""PLAN 18.10 — a v2 workspace's analysis runs the v2 pipeline end to end."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.analysis_worker import SqlAnalysisWorker
from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.models import AnalysisJobRow
from career_assistant.adapters.persistence.pipeline_store import (
    SqlPipelineVersionStore,
)
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.api.deps import WORKSPACE_COOKIE
from career_assistant.main import create_app

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[3] / "sample-data" / "fixtures"
CV = (FIXTURES / "resumes" / "cv-strong-match.txt").read_text(encoding="utf-8")
JD = (FIXTURES / "job-descriptions" / "jd-clean-match.txt").read_text(encoding="utf-8")


def _app(
    session_factory: sessionmaker[Session],
) -> tuple[TestClient, SqlAnalysisWorker, Callable[[], SqlUnitOfWork]]:
    def uow_factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    cv_store = SqlCvStore(uow_factory)
    client = TestClient(
        create_app(
            cv_store=cv_store,
            role_store=SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory),
            pipeline_store=SqlPipelineVersionStore(uow_factory),
        )
    )
    return client, SqlAnalysisWorker(uow_factory), uow_factory


def _analyse(client: TestClient, worker: SqlAnalysisWorker) -> tuple[str, str]:
    assert (
        client.post("/api/cv", json={"text": CV, "filename": "cv.txt"}).status_code
        == 201
    )
    created = client.post(
        "/api/roles",
        json={"title": "Data Engineer", "company": "Northwind", "description": JD},
    )
    assert created.status_code == 202
    worker.drain()
    return created.json()["role"]["id"], created.json()["jobId"]


def _job_pipeline(session_factory: sessionmaker[Session], job_id: str) -> str:
    with session_factory() as session:
        return session.scalars(
            select(AnalysisJobRow.pipeline_version).where(
                AnalysisJobRow.id == uuid.UUID(job_id)
            )
        ).one()


def test_a_v2_workspace_is_analysed_and_scored_by_the_v2_pipeline(
    session_factory: sessionmaker[Session],
) -> None:
    client, worker, uow_factory = _app(session_factory)
    client.put("/api/settings/pipeline", json={"pipelineVersion": "v2"})

    role_id, job_id = _analyse(client, worker)

    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["state"] == "succeeded", job
    role = client.get(f"/api/roles/{role_id}").json()
    assert role["status"] == "ready"
    assert _job_pipeline(session_factory, job_id) == "v2"
    workspace = client.cookies[WORKSPACE_COOKIE]
    with uow_factory() as uow:
        result = uow.v2.result(workspace, role_id)
    assert result is not None
    assert result.analysis_id == job_id
    assert result.verdicts
    assert role["fitScore"] == round(result.score)


def test_a_default_workspace_still_runs_v1(
    session_factory: sessionmaker[Session],
) -> None:
    client, worker, uow_factory = _app(session_factory)

    role_id, job_id = _analyse(client, worker)

    assert client.get(f"/api/jobs/{job_id}").json()["state"] == "succeeded"
    assert _job_pipeline(session_factory, job_id) == "v1"
    with uow_factory() as uow:
        assert uow.v2.result(client.cookies[WORKSPACE_COOKIE], role_id) is None
