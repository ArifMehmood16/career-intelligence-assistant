"""Progress over HTTP: tasks done of total, elapsed and remaining time, queue."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.support.v2_http import JD, SqlApp, analyse, queue_role, sql_app

from career_assistant.adapters.persistence.progress import sql_progress
from career_assistant.domain.pipeline import PipelineVersion
from career_assistant.domain.progress import TaskKey

pytestmark = pytest.mark.integration

_KEYS = ["prepare", "read_cv", "read_advert", "search", "judge", "recheck", "score"]


def _add_role(app: SqlApp, title: str) -> tuple[str, str]:
    """Add a role to the CV already uploaded. Returns role and job ids."""
    created = app.client.post(
        "/api/roles", json={"title": title, "company": "Acme", "description": JD}
    ).json()
    return created["role"]["id"], created["jobId"]


def _job(app: SqlApp, job_id: str) -> dict[str, object]:
    response = app.client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    return response.json()  # type: ignore[no-any-return]


def test_a_queued_job_lists_its_planned_tasks_and_its_place_in_the_queue(
    session_factory: sessionmaker[Session],
) -> None:
    app = sql_app(session_factory)
    _role, first = queue_role(app)
    _second_role, second = _add_role(app, "Second")

    progress = _job(app, second)["progress"]

    assert progress["tasksDone"] == 0
    assert progress["tasksTotal"] == 7
    assert progress["currentTask"] is None
    assert progress["elapsedSeconds"] is None
    assert progress["queuePosition"] == 1
    assert progress["remainingSeconds"] is None, "no finished analysis to go on"
    assert [t["key"] for t in progress["tasks"]] == _KEYS
    assert {t["state"] for t in progress["tasks"]} == {"pending"}
    assert _job(app, first)["progress"]["queuePosition"] == 0


def test_a_running_job_reports_the_task_it_is_on(
    session_factory: sessionmaker[Session],
) -> None:
    app = sql_app(session_factory)
    role_id, job_id = queue_role(app)
    job = app.worker.claim_next()
    assert job is not None
    progress = sql_progress(
        app.uow_factory, job, PipelineVersion.V2, lambda: datetime.now(UTC)
    )
    progress.enter(TaskKey.PREPARE)
    progress.enter(TaskKey.READ_ADVERT)

    body = _job(app, job_id)["progress"]

    assert (body["tasksDone"], body["tasksTotal"]) == (1, 7)
    assert body["currentTask"] == "read_advert"
    assert body["elapsedSeconds"] >= 0
    assert body["queuePosition"] is None
    assert [t["state"] for t in body["tasks"]][:3] == ["done", "pending", "running"]
    role = app.client.get(f"/api/roles/{role_id}").json()
    assert role["activeJob"]["id"] == job_id
    assert role["activeJob"]["progress"]["currentTask"] == "read_advert"


def test_an_undiscovered_optional_stage_does_not_fabricate_a_time_estimate(
    session_factory: sessionmaker[Session],
) -> None:
    app = sql_app(session_factory)
    _first_role, first_job = analyse(app)
    _role, second = _add_role(app, "Second")

    finished = _job(app, first_job)["progress"]
    queued = _job(app, second)["progress"]

    assert (finished["tasksDone"], finished["remainingSeconds"]) == (7, 0)
    # A skipped corrective stage has no measured duration; queued jobs have not
    # discovered whether they need it. Stage planning resolves that uncertainty.
    assert queued["remainingSeconds"] is None


def test_the_roles_list_carries_each_active_job_and_nothing_for_ready_roles(
    session_factory: sessionmaker[Session],
) -> None:
    app = sql_app(session_factory)
    ready_role, _job_id = analyse(app)
    waiting_role, waiting_job = _add_role(app, "Waiting")

    listed = {role["id"]: role for role in app.client.get("/api/roles").json()}

    assert listed[ready_role]["activeJob"] is None
    active = listed[waiting_role]["activeJob"]
    assert active["id"] == waiting_job
    assert active["state"] == "queued"
    assert active["progress"]["tasksTotal"] == 7
