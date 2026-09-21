"""Phase 13A.3 — PostgreSQL analysis worker is the production path."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.analysis_worker import SqlAnalysisWorker
from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ports.extraction import (
    RequirementExtractionPort,
    RequirementExtractionResult,
)
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.jobs import JobState, mark_running
from career_assistant.main import create_app

pytestmark = pytest.mark.integration

_CV = """Experience
Senior Analytics Engineer — Acme — 2022-01 — Present
- Owned dbt models in production for the warehouse.
"""

_JD = """Requirements
- Must have production dbt experience
"""


class _BoomRequirements(RequirementExtractionPort):
    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> RequirementExtractionResult:
        raise RuntimeError("extractor exploded")


def _uow_factory(session_factory: sessionmaker[Session]):
    def factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    return factory


def _sql_app(
    session_factory: sessionmaker[Session],
    *,
    worker: SqlAnalysisWorker | None = None,
) -> tuple[TestClient, SqlAnalysisWorker]:
    uow_factory = _uow_factory(session_factory)
    cv_store = SqlCvStore(uow_factory)
    resolved_worker = worker or SqlAnalysisWorker(uow_factory)
    client = TestClient(
        create_app(
            cv_store=cv_store,
            role_store=SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory),
        )
    )
    return client, resolved_worker


def test_post_role_returns_analysing_and_queued_before_worker_runs(
    session_factory: sessionmaker[Session],
) -> None:
    client, _worker = _sql_app(session_factory)
    uploaded = client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    assert uploaded.status_code == 201

    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    assert created.status_code == 202
    body = created.json()
    assert body["role"]["status"] == "analysing"
    assert body["role"]["fitScore"] == 0
    assert body["role"]["bandLabel"] == "Not scored yet"
    assert body["jobId"]

    listed = client.get("/api/roles")
    assert listed.status_code == 200
    assert listed.json()[0]["status"] == "analysing"

    requirements = client.get(f"/api/roles/{body['role']['id']}/requirements")
    assert requirements.status_code == 409

    job = client.get(f"/api/jobs/{body['jobId']}")
    assert job.status_code == 200
    assert job.json()["id"] == body["jobId"]
    assert job.json()["state"] == "queued"
    assert job.json()["stage"] is None


def test_worker_runs_queued_through_running_to_succeeded(
    session_factory: sessionmaker[Session],
) -> None:
    client, worker = _sql_app(session_factory)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    body = created.json()
    role_id = body["role"]["id"]
    job_id = body["jobId"]

    claimed = worker.claim_next()
    assert claimed is not None
    assert claimed.id == job_id
    assert claimed.state is JobState.RUNNING
    running = client.get(f"/api/jobs/{job_id}")
    assert running.json()["state"] == "running"
    assert client.get(f"/api/roles/{role_id}").json()["status"] == "analysing"

    done = worker.complete(claimed)
    assert done.state is JobState.SUCCEEDED
    assert client.get(f"/api/jobs/{job_id}").json()["state"] == "succeeded"
    role = client.get(f"/api/roles/{role_id}").json()
    assert role["status"] == "ready"
    assert role["fitScore"] > 0
    requirements = client.get(f"/api/roles/{role_id}/requirements")
    assert requirements.status_code == 200
    assert requirements.json()


def test_worker_failure_marks_failed_without_partial_results(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = _uow_factory(session_factory)
    worker = SqlAnalysisWorker(uow_factory, requirement_extractor=_BoomRequirements())
    client, _ = _sql_app(session_factory, worker=worker)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    role_id = created.json()["role"]["id"]
    job_id = created.json()["jobId"]

    done = worker.process_next()
    assert done is not None
    assert done.state is JobState.FAILED
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["state"] == "failed"
    assert "extracting_requirements_failed" in (job["error"] or "")
    assert client.get(f"/api/roles/{role_id}").json()["status"] == "failed"
    assert client.get(f"/api/roles/{role_id}/requirements").status_code == 409
    with uow_factory() as uow:
        assert uow.analysis.list_mappings(client.cookies["workspace"], role_id) == ()


def test_reanalyse_returns_analysing_and_queued_before_worker_runs(
    session_factory: sessionmaker[Session],
) -> None:
    client, worker = _sql_app(session_factory)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    role_id = created.json()["role"]["id"]
    worker.drain()
    assert client.get(f"/api/roles/{role_id}").json()["status"] == "ready"

    reanalysed = client.post(f"/api/roles/{role_id}/reanalyse")
    assert reanalysed.status_code == 202
    assert reanalysed.json()["jobId"] != created.json()["jobId"]
    assert client.get(f"/api/roles/{role_id}").json()["status"] == "analysing"
    assert client.get(f"/api/roles/{role_id}").json()["fitScore"] == 0
    job = client.get(f"/api/jobs/{reanalysed.json()['jobId']}")
    assert job.json()["state"] == "queued"
    assert client.get(f"/api/roles/{role_id}/requirements").status_code == 409


def test_cv_replace_enqueues_jobs_and_never_leaves_ready_with_stale_score(
    session_factory: sessionmaker[Session],
) -> None:
    client, worker = _sql_app(session_factory)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    role_id = created.json()["role"]["id"]
    worker.drain()
    first_score = client.get(f"/api/roles/{role_id}").json()["fitScore"]
    assert first_score > 0

    replaced = client.post(
        "/api/cv",
        json={
            "text": _CV + "\n- Also shipped Looker dashboards.\n",
            "filename": "cv2.txt",
        },
    )
    assert replaced.status_code == 201
    job_ids = replaced.json()["reanalysis"]["jobIds"]
    assert len(job_ids) == 1
    role = client.get(f"/api/roles/{role_id}").json()
    assert role["status"] == "analysing"
    assert role["fitScore"] == 0
    assert client.get(f"/api/jobs/{job_ids[0]}").json()["state"] == "queued"
    assert client.get(f"/api/roles/{role_id}/requirements").status_code == 409

    worker.drain()
    ready = client.get(f"/api/roles/{role_id}").json()
    assert ready["status"] == "ready"
    assert ready["fitScore"] > 0


def test_cv_delete_marks_roles_failed(
    session_factory: sessionmaker[Session],
) -> None:
    client, worker = _sql_app(session_factory)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    role_id = created.json()["role"]["id"]
    worker.drain()
    assert client.get(f"/api/roles/{role_id}").json()["status"] == "ready"

    deleted = client.delete("/api/cv")
    assert deleted.status_code == 204
    assert client.get("/api/cv").json() is None
    role = client.get(f"/api/roles/{role_id}").json()
    assert role["status"] == "failed"
    assert client.get(f"/api/roles/{role_id}/requirements").status_code == 409


def test_startup_recovers_queued_and_stale_running_jobs(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = _uow_factory(session_factory)
    client, _worker = _sql_app(session_factory)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    queued_role = client.post(
        "/api/roles",
        json={"title": "Queued", "company": "Acme", "description": _JD},
    ).json()
    stale_role = client.post(
        "/api/roles",
        json={"title": "Stale", "company": "Acme", "description": _JD},
    ).json()
    workspace_id = client.cookies["workspace"]
    stale_started = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)

    with uow_factory() as uow:
        stale_job = uow.jobs.get(workspace_id, stale_role["jobId"])
        assert stale_job is not None
        uow.jobs.save(mark_running(stale_job, at=stale_started))
        uow.commit()

    recovered = SqlAnalysisWorker(
        uow_factory,
        clock=lambda: stale_started + timedelta(minutes=20),
        running_timeout=timedelta(minutes=15),
    ).startup()
    assert stale_role["jobId"] in recovered.failed_job_ids
    assert queued_role["jobId"] in recovered.dispatched_job_ids

    assert client.get(f"/api/jobs/{stale_role['jobId']}").json()["state"] == "failed"
    assert (
        client.get(f"/api/roles/{stale_role['role']['id']}").json()["status"]
        == "failed"
    )
    assert client.get(f"/api/jobs/{queued_role['jobId']}").json()["state"] == "queued"
    assert (
        client.get(f"/api/roles/{queued_role['role']['id']}").json()["status"]
        == "analysing"
    )
