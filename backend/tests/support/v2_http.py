"""A SQL-backed app and worker for driving a v1 or v2 analysis over HTTP."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.analysis_worker import SqlAnalysisWorker
from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.pipeline_store import (
    SqlPipelineVersionStore,
)
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.adapters.persistence.v2_result_reader import SqlV2ResultReader
from career_assistant.main import create_app

FIXTURES = Path(__file__).resolve().parents[3] / "sample-data" / "fixtures"
CV = (FIXTURES / "resumes" / "cv-strong-match.txt").read_text(encoding="utf-8")
JD = (FIXTURES / "job-descriptions" / "jd-clean-match.txt").read_text(encoding="utf-8")


@dataclass(frozen=True, slots=True)
class SqlApp:
    client: TestClient
    worker: SqlAnalysisWorker
    uow_factory: Callable[[], SqlUnitOfWork]


def sql_app(session_factory: sessionmaker[Session]) -> SqlApp:
    def uow_factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    cv_store = SqlCvStore(uow_factory)
    client = TestClient(
        create_app(
            cv_store=cv_store,
            role_store=SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory),
            pipeline_store=SqlPipelineVersionStore(uow_factory),
            v2_results=SqlV2ResultReader(uow_factory),
        )
    )
    return SqlApp(client, SqlAnalysisWorker(uow_factory), uow_factory)


def analyse(app: SqlApp) -> tuple[str, str]:
    """Upload the CV, add the role and drain the worker. Returns role and job ids."""
    posted = app.client.post("/api/cv", json={"text": CV, "filename": "cv.txt"})
    assert posted.status_code == 201
    created = app.client.post(
        "/api/roles",
        json={"title": "Data Engineer", "company": "Northwind", "description": JD},
    )
    assert created.status_code == 202
    app.worker.drain()
    return created.json()["role"]["id"], created.json()["jobId"]
