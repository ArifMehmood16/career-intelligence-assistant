"""Progress for one workspace's analysis jobs, for the roles and jobs routes."""

from __future__ import annotations

from datetime import datetime

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.domain.jobs import LIVE_STATES, AnalysisJob, JobState
from career_assistant.domain.pipeline import PipelineVersion
from career_assistant.domain.progress import (
    JobTask,
    ProgressView,
    TaskBaseline,
    TaskKey,
    baselines_from,
    pipeline_of,
    plan_for,
    progress_view,
)

# Recent successful analyses whose task durations make the estimate.
HISTORY_JOBS = 10


class WorkspaceProgress:
    """Reads the workspace's live jobs and their tasks once; views are then cheap."""

    def __init__(self, uow: SqlUnitOfWork, workspace_id: str, *, now: datetime) -> None:
        self._uow = uow
        self._workspace_id = workspace_id
        self._now = now
        self._live = uow.jobs.live_for_workspace(workspace_id)
        self._tasks = uow.job_tasks.for_jobs(
            workspace_id, [job.id for job in self._live]
        )
        self._pipeline = uow.workspaces.pipeline_version(workspace_id)
        self._baselines: dict[PipelineVersion, dict[TaskKey, TaskBaseline]] = {}

    def active_for_role(self, role_id: str) -> AnalysisJob | None:
        return next((job for job in self._live if job.role_id == role_id), None)

    def view(self, job: AnalysisJob) -> ProgressView:
        tasks = self._tasks_of(job)
        ahead = (
            [self._tasks_of(other) for other in self._ahead_of(job)]
            if job.state is JobState.QUEUED
            else []
        )
        pipelines = {pipeline_of(t) for t in (*ahead, tasks)}
        return progress_view(
            state=job.state,
            started_at=job.started_at,
            finished_at=job.finished_at,
            tasks=tasks,
            now=self._now,
            baselines={p: self._baseline(p) for p in pipelines if p is not None},
            ahead=ahead,
        )

    def _tasks_of(self, job: AnalysisJob) -> tuple[JobTask, ...]:
        if job.id in self._tasks:
            return self._tasks[job.id]
        if job.state in LIVE_STATES:
            # Not started yet: the plan the workspace's pipeline will run.
            return plan_for(self._pipeline)
        return self._uow.job_tasks.for_job(self._workspace_id, job.id)

    def _ahead_of(self, job: AnalysisJob) -> list[AnalysisJob]:
        """Running jobs, then queued jobs the worker takes before this one."""
        position = next(
            (i for i, other in enumerate(self._live) if other.id == job.id),
            len(self._live),
        )
        return [
            other
            for i, other in enumerate(self._live)
            if other.id != job.id and (other.state is JobState.RUNNING or i < position)
        ]

    def _baseline(self, pipeline: PipelineVersion) -> dict[TaskKey, TaskBaseline]:
        if pipeline not in self._baselines:
            samples = self._uow.job_tasks.recent_samples(
                self._workspace_id, pipeline, jobs=HISTORY_JOBS
            )
            self._baselines[pipeline] = baselines_from(samples)
        return self._baselines[pipeline]
