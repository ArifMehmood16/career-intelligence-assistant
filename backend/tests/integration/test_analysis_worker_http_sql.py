"""Phase 13A.3 — PostgreSQL analysis worker is the production path."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, SecretStr
from sqlalchemy.orm import Session, sessionmaker
from tests.support.structured_transport import StructuredTransport

from career_assistant.adapters.persistence.analysis_repos import (
    SqlAnalysisJobRepository,
)
from career_assistant.adapters.persistence.analysis_worker import SqlAnalysisWorker
from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.provider_settings_store import (
    SqlProviderSettingsStore,
)
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.adapters.persistence.v2_result_reader import SqlV2ResultReader
from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.application.contracts.chunking import JobChunkResponse
from career_assistant.application.contracts.judge import JudgeResponse
from career_assistant.application.ports.errors import ProviderUnavailableError
from career_assistant.application.ports.structured import (
    StructuredRequest,
    StructuredResult,
)
from career_assistant.domain.jobs import (
    JobError,
    JobStage,
    JobState,
    mark_failed,
    mark_running,
)
from career_assistant.main import create_app
from career_assistant.settings import ProviderSettings

pytestmark = pytest.mark.integration

_CV = """Experience
Senior Analytics Engineer — Acme — January 2022 – Present
- Owned dbt models in production for the warehouse.
"""

_JD = """Requirements
- Must have production dbt experience
"""


class _BoomStructured(HermeticStructuredCompleter):
    def complete_structured[T: BaseModel](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]:
        if request.contract is JobChunkResponse:
            raise RuntimeError("scripted document failure")
        return super().complete_structured(request)


class _HeldJudge(HermeticStructuredCompleter):
    def __init__(self, *, fail_after_release: bool) -> None:
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()
        self.finished = threading.Event()
        self.fail_after_release = fail_after_release
        self.judge_calls = 0

    def complete_structured[T: BaseModel](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]:
        if request.contract is not JudgeResponse:
            return super().complete_structured(request)
        self.judge_calls += 1
        self.entered.set()
        assert self.release.wait(timeout=10), "test did not release the provider"
        self.finished.set()
        if self.fail_after_release:
            raise ProviderUnavailableError("scripted late failure")
        return super().complete_structured(request)


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
            v2_results=SqlV2ResultReader(uow_factory),
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

    requirements = client.get(f"/api/roles/{body['role']['id']}/verdicts")
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
    requirements = client.get(f"/api/roles/{role_id}/verdicts")
    assert requirements.status_code == 200
    assert requirements.json()["verdicts"]


@pytest.mark.parametrize("fail_after_release", [False, True])
def test_running_worker_expires_a_blocked_judge_before_it_returns(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    fail_after_release: bool,
) -> None:
    provider = _HeldJudge(fail_after_release=fail_after_release)
    monkeypatch.setattr(
        "career_assistant.adapters.persistence.analysis_worker.build_structured_port",
        lambda *_args, **_kwargs: provider,
    )
    clock = [datetime(2026, 10, 5, tzinfo=UTC)]
    worker = SqlAnalysisWorker(_uow_factory(session_factory), clock=lambda: clock[0])
    client, _ = _sql_app(session_factory, worker=worker)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    body = client.post(
        "/api/roles", json={"title": "AE", "company": "Acme", "description": _JD}
    ).json()
    job_path = f"/api/jobs/{body['jobId']}"
    role_path = f"/api/roles/{body['role']['id']}"
    stop = threading.Event()
    thread = threading.Thread(
        target=worker.run_forever, args=(stop,), kwargs={"idle_wait_seconds": 0.01}
    )
    thread.start()
    try:
        assert provider.entered.wait(timeout=5)
        assert client.get(job_path).json()["state"] == "running"
        clock[0] += timedelta(minutes=16)
        deadline = time.monotonic() + 2
        expired = client.get(job_path).json()
        while expired["state"] == "running" and time.monotonic() < deadline:
            stop.wait(timeout=0.02)
            expired = client.get(job_path).json()
        assert expired["state"] == "failed", "expiry must not require worker restart"
        assert expired["error"]["code"] == "stale_running"
        assert not provider.finished.is_set()
        assert client.get(role_path).json()["status"] == "failed"
        assert client.get(f"{role_path}/verdicts").status_code == 409
        judge = next(t for t in expired["progress"]["tasks"] if t["key"] == "judge")
        assert judge["state"] == "failed"
        assert judge["unitsDone"] == 0
    finally:
        stop.set()
        provider.release.set()
        thread.join(timeout=5)
    assert not thread.is_alive()
    assert client.get(job_path).json()["error"]["code"] == "stale_running"
    assert client.get(f"{role_path}/verdicts").status_code == 409
    assert provider.judge_calls == 1


def test_worker_failure_marks_failed_without_partial_results(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uow_factory = _uow_factory(session_factory)
    monkeypatch.setattr(
        "career_assistant.adapters.persistence.analysis_worker.build_structured_port",
        lambda *_args, **_kwargs: _BoomStructured(),
    )
    worker = SqlAnalysisWorker(uow_factory)
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
    error = job["error"]
    if isinstance(error, dict):
        assert error["code"] == "mapping_failed"
    else:
        assert "mapping_failed" in (error or "")
    assert client.get(f"/api/roles/{role_id}").json()["status"] == "failed"
    assert client.get(f"/api/roles/{role_id}/verdicts").status_code == 409
    with uow_factory() as uow:
        assert uow.v2.result(client.cookies["workspace"], role_id) is None


@pytest.mark.parametrize("terminal", ["expired", "succeeded", "deleted"])
def test_late_worker_failure_preserves_terminal_or_deleted_jobs(
    session_factory: sessionmaker[Session], terminal: str
) -> None:
    client, worker = _sql_app(session_factory)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    body = client.post(
        "/api/roles", json={"title": "AE", "company": "Acme", "description": _JD}
    ).json()
    claimed = worker.claim_next()
    assert claimed is not None
    if terminal == "succeeded":
        expected = worker.complete(claimed)
        assert expected.state is JobState.SUCCEEDED
    elif terminal == "expired":
        expected = mark_failed(
            claimed,
            at=datetime.now(UTC),
            error=JobError(
                "stale_running", "Analysis exceeded its running time limit."
            ),
        )
        with _uow_factory(session_factory)() as uow:
            uow.analysis.fail_job(
                workspace_id=claimed.workspace_id, role_id=claimed.role_id, job=expected
            )
            uow.commit()
    else:
        assert client.delete(f"/api/roles/{claimed.role_id}").status_code == 204
        expected = claimed

    result = worker._record_failure(claimed, JobStage.MAPPING, RuntimeError("late"))
    assert result == expected
    with _uow_factory(session_factory)() as uow:
        saved = uow.jobs.get(claimed.workspace_id, claimed.id)
    assert saved == (None if terminal == "deleted" else expected)
    if terminal == "succeeded":
        assert (
            client.get(f"/api/roles/{body['role']['id']}/verdicts").status_code == 200
        )


def test_expiry_rechecks_a_job_completed_since_the_running_snapshot(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, worker = _sql_app(session_factory)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    client.post(
        "/api/roles", json={"title": "AE", "company": "Acme", "description": _JD}
    )
    running = worker.claim_next()
    assert running is not None
    done = worker.complete(running)
    assert done.state is JobState.SUCCEEDED
    # Simulate publication completing after the sweep selected a running row.
    monkeypatch.setattr(SqlAnalysisJobRepository, "list_running", lambda _: (running,))
    recovery = SqlAnalysisWorker(
        _uow_factory(session_factory),
        clock=lambda: datetime.now(UTC) + timedelta(minutes=16),
    ).startup()
    assert recovery.failed_job_ids == ()
    assert client.get(f"/api/jobs/{done.id}").json()["state"] == "succeeded"
    assert client.get(f"/api/roles/{done.role_id}/verdicts").status_code == 200


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
    assert client.get(f"/api/roles/{role_id}/verdicts").status_code == 409


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
    assert client.get(f"/api/roles/{role_id}/verdicts").status_code == 409

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
    assert client.get(f"/api/roles/{role_id}/verdicts").status_code == 409


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


def test_worker_extraction_calls_the_selected_scripted_provider(
    session_factory: sessionmaker[Session],
) -> None:
    transport = StructuredTransport()
    settings = ProviderSettings(
        completion_provider="hermetic",
        embedding_provider="hermetic",
        allow_hosted_providers=True,
        openai_api_key=SecretStr("sk-test-never-leave-the-fixture"),
        openai_completion_model="gpt-4o-mini",
        openai_embedding_model="text-embedding-3-small",
    )
    uow_factory = _uow_factory(session_factory)
    cv_store = SqlCvStore(uow_factory)
    worker = SqlAnalysisWorker(uow_factory, providers=settings, transport=transport)
    client = TestClient(
        create_app(
            providers=settings,
            cv_store=cv_store,
            role_store=SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory),
            provider_choice_store=SqlProviderSettingsStore(uow_factory),
            v2_results=SqlV2ResultReader(uow_factory),
        )
    )
    uploaded = client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    assert uploaded.status_code == 201
    chosen = client.put(
        "/api/settings/providers",
        json={
            "answerProviderId": "openai",
            "answerModel": "gpt-4o-mini",
            "indexProviderId": "hermetic",
            "indexModel": "lexical-hash-v1",
            "acknowledgedEgress": True,
        },
    )
    assert chosen.status_code == 200
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    assert created.status_code == 202
    worker.drain()
    assert transport.calls
    assert any("/chat/completions" in url for _method, url in transport.calls)
    role_id = created.json()["role"]["id"]
    role = client.get(f"/api/roles/{role_id}")
    assert role.status_code == 200
    assert role.json()["status"] == "ready"
