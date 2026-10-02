"""Analysis progress rows: counts and timestamps per task, deleted with the job."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from tests.integration.conftest import make_document

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.jobs import (
    JobError,
    RoleStatus,
    mark_failed,
    mark_running,
    mark_succeeded,
    new_role_analysis_job,
)
from career_assistant.domain.pipeline import PipelineVersion
from career_assistant.domain.progress import (
    JobTask,
    TaskKey,
    TaskSample,
    TaskState,
    advance,
    call_finished,
    enter,
    finish,
    plan_calls,
    plan_for,
    skip,
)

pytestmark = pytest.mark.integration

T0 = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def _at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def _role(uow: SqlUnitOfWork, ws: str) -> str:
    jd = uow.documents.save_admitted(
        ws,
        make_document(
            kind=DocumentKind.JOB_DESCRIPTION, text="Python", is_active=False
        ),
    )
    role_id = str(uuid.uuid4())
    uow.roles.create(
        workspace_id=ws,
        role_id=role_id,
        title="AE",
        company="Acme",
        job_description_document_id=jd.id,
        status=RoleStatus.ANALYSING,
    )
    return role_id


def _job(
    uow: SqlUnitOfWork,
    ws: str,
    *,
    pipeline: PipelineVersion = PipelineVersion.V2,
    finished: float | None = None,
    failed: bool = False,
) -> str:
    """A job for a new role: queued, or finished `finished` seconds after T0."""
    job = new_role_analysis_job(
        job_id=str(uuid.uuid4()),
        workspace_id=ws,
        role_id=_role(uow, ws),
        created_at=T0,
    )
    uow.jobs.enqueue(job)
    uow.jobs.set_pipeline_version(ws, job.id, pipeline)
    if finished is not None:
        running = mark_running(job, at=T0)
        end = _at(finished)
        uow.jobs.save(
            mark_failed(running, at=end, error=JobError("x", "failed"))
            if failed
            else mark_succeeded(running, at=end)
        )
    return job.id


def _done_v2(judge_seconds: float, requirements: int) -> tuple[JobTask, ...]:
    tasks = plan_for(PipelineVersion.V2)
    tasks = enter(tasks, TaskKey.PREPARE, at=_at(0))
    tasks = enter(tasks, TaskKey.READ_CV, at=_at(1))
    tasks = enter(tasks, TaskKey.READ_ADVERT, at=_at(11))
    tasks = enter(tasks, TaskKey.JUDGE, at=_at(31))
    tasks = advance(tasks, TaskKey.JUDGE, units_done=0, units_total=requirements)
    tasks = finish(tasks, TaskKey.JUDGE, at=_at(31 + judge_seconds))
    tasks = skip(tasks, TaskKey.RECHECK, at=_at(31 + judge_seconds))
    tasks = enter(tasks, TaskKey.SCORE, at=_at(31 + judge_seconds))
    return finish(tasks, TaskKey.SCORE, at=_at(32 + judge_seconds))


def test_task_rows_round_trip_in_plan_order(uow: SqlUnitOfWork) -> None:
    ws = str(uuid.uuid4())
    tasks = enter(plan_for(PipelineVersion.V2), TaskKey.PREPARE, at=_at(0))
    tasks = enter(tasks, TaskKey.READ_CV, at=_at(2))
    tasks = plan_calls(tasks, TaskKey.READ_CV, model=2, embedding=1)
    tasks = call_finished(tasks, TaskKey.READ_CV, operation="model")
    with uow:
        uow.workspaces.ensure(ws)
        job_id = _job(uow, ws)
        uow.job_tasks.put(ws, job_id, tasks)
        uow.commit()

    with uow:
        assert uow.job_tasks.for_job(ws, job_id) == tasks
        assert uow.job_tasks.for_job(str(uuid.uuid4()), job_id) == ()


def test_putting_tasks_again_replaces_them(uow: SqlUnitOfWork) -> None:
    ws = str(uuid.uuid4())
    first = enter(plan_for(PipelineVersion.V2), TaskKey.PREPARE, at=_at(0))
    later = advance(
        enter(first, TaskKey.READ_CV, at=_at(3)),
        TaskKey.READ_CV,
        units_done=1,
        units_total=2,
    )
    with uow:
        uow.workspaces.ensure(ws)
        job_id = _job(uow, ws)
        uow.job_tasks.put(ws, job_id, first)
        uow.job_tasks.put(ws, job_id, later)
        uow.commit()

    with uow:
        stored = uow.job_tasks.for_job(ws, job_id)
    assert stored == later
    assert [t.state for t in stored[:2]] == [TaskState.DONE, TaskState.RUNNING]


def test_tasks_for_several_jobs_come_back_keyed_by_job(uow: SqlUnitOfWork) -> None:
    ws = str(uuid.uuid4())
    with uow:
        uow.workspaces.ensure(ws)
        first, second, idle = _job(uow, ws), _job(uow, ws), _job(uow, ws)
        uow.job_tasks.put(ws, first, plan_for(PipelineVersion.V2))
        uow.job_tasks.put(ws, second, plan_for(PipelineVersion.V2))
        uow.commit()

    with uow:
        found = uow.job_tasks.for_jobs(ws, (first, second, idle))
    assert found == {
        first: plan_for(PipelineVersion.V2),
        second: plan_for(PipelineVersion.V2),
    }


def test_deleting_the_role_deletes_its_task_rows(uow: SqlUnitOfWork) -> None:
    ws = str(uuid.uuid4())
    with uow:
        uow.workspaces.ensure(ws)
        job_id = _job(uow, ws)
        uow.job_tasks.put(ws, job_id, plan_for(PipelineVersion.V2))
        role_id = uow.jobs.get(ws, job_id).role_id  # type: ignore[union-attr]
        uow.commit()

    with uow:
        uow.roles.delete(ws, role_id)
        uow.commit()

    with uow:
        assert uow.job_tasks.for_job(ws, job_id) == ()


def test_samples_come_from_recent_successful_jobs_of_the_same_pipeline(
    uow: SqlUnitOfWork,
) -> None:
    ws, other = str(uuid.uuid4()), str(uuid.uuid4())
    with uow:
        uow.workspaces.ensure(ws)
        uow.workspaces.ensure(other)
        oldest = _job(uow, ws, finished=100)
        newer = _job(uow, ws, finished=200)
        newest = _job(uow, ws, finished=300)
        failed = _job(uow, ws, finished=400, failed=True)
        elsewhere = _job(uow, other, finished=600)
        running = _job(uow, ws)
        for job_id, seconds in [
            (oldest, 90),
            (newer, 40),
            (newest, 60),
            (failed, 5),
            (elsewhere, 7),
        ]:
            uow.job_tasks.put(
                other if job_id == elsewhere else ws, job_id, _done_v2(seconds, 10)
            )
        uow.job_tasks.put(
            ws, running, enter(plan_for(PipelineVersion.V2), TaskKey.PREPARE, at=T0)
        )
        uow.commit()

    with uow:
        samples = uow.job_tasks.recent_samples(ws, PipelineVersion.V2, jobs=2)

    judged = sorted(s.seconds for s in samples if s.key is TaskKey.JUDGE)
    assert judged == [40, 60]
    assert TaskSample(TaskKey.READ_ADVERT, seconds=20, units=None) in samples
    assert all(s.key is not TaskKey.RECHECK for s in samples), "skipped is no sample"
    assert {s.units for s in samples if s.key is TaskKey.JUDGE} == {10}
