"""Analysis job task rows: progress for the API and samples for the estimate."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from career_assistant.adapters.persistence.models import (
    AnalysisJobRow,
    AnalysisJobTaskRow,
)
from career_assistant.domain.jobs import JobState
from career_assistant.domain.pipeline import PipelineVersion
from career_assistant.domain.progress import JobTask, TaskKey, TaskSample, TaskState


class SqlJobTaskRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def put(self, workspace_id: str, job_id: str, tasks: Sequence[JobTask]) -> None:
        """Replace the job's task rows with `tasks`, in plan order."""
        wid, jid = uuid.UUID(workspace_id), uuid.UUID(job_id)
        self._session.execute(
            delete(AnalysisJobTaskRow).where(
                AnalysisJobTaskRow.workspace_id == wid,
                AnalysisJobTaskRow.job_id == jid,
            )
        )
        self._session.add_all(
            _to_row(wid, jid, position, task) for position, task in enumerate(tasks)
        )
        self._session.flush()

    def for_job(self, workspace_id: str, job_id: str) -> tuple[JobTask, ...]:
        return self.for_jobs(workspace_id, (job_id,)).get(job_id, ())

    def for_jobs(
        self, workspace_id: str, job_ids: Sequence[str]
    ) -> dict[str, tuple[JobTask, ...]]:
        if not job_ids:
            return {}
        rows = self._session.scalars(
            select(AnalysisJobTaskRow)
            .where(
                AnalysisJobTaskRow.workspace_id == uuid.UUID(workspace_id),
                AnalysisJobTaskRow.job_id.in_([uuid.UUID(j) for j in job_ids]),
            )
            .order_by(AnalysisJobTaskRow.job_id, AnalysisJobTaskRow.position)
        ).all()
        found: dict[str, list[JobTask]] = defaultdict(list)
        for row in rows:
            found[str(row.job_id)].append(_to_task(row))
        return {job_id: tuple(tasks) for job_id, tasks in found.items()}

    def recent_samples(
        self, workspace_id: str, pipeline: PipelineVersion, *, jobs: int
    ) -> tuple[TaskSample, ...]:
        """Finished tasks of the workspace's last `jobs` successful analyses."""
        recent = (
            select(AnalysisJobRow.id)
            .where(
                AnalysisJobRow.workspace_id == uuid.UUID(workspace_id),
                AnalysisJobRow.state == JobState.SUCCEEDED.value,
                AnalysisJobRow.pipeline_version == pipeline.value,
                AnalysisJobRow.finished_at.is_not(None),
            )
            .order_by(AnalysisJobRow.finished_at.desc())
            .limit(jobs)
        )
        rows = self._session.scalars(
            select(AnalysisJobTaskRow).where(
                AnalysisJobTaskRow.job_id.in_(recent.scalar_subquery()),
                AnalysisJobTaskRow.state == TaskState.DONE.value,
                AnalysisJobTaskRow.started_at.is_not(None),
                AnalysisJobTaskRow.finished_at.is_not(None),
            )
        ).all()
        return tuple(
            TaskSample(
                key=TaskKey(row.key),
                seconds=(row.finished_at - row.started_at).total_seconds(),
                units=row.units_total,
            )
            for row in rows
            if row.started_at is not None and row.finished_at is not None
        )


def _to_row(
    workspace_id: uuid.UUID, job_id: uuid.UUID, position: int, task: JobTask
) -> AnalysisJobTaskRow:
    return AnalysisJobTaskRow(
        job_id=job_id,
        key=task.key.value,
        workspace_id=workspace_id,
        position=position,
        state=task.state.value,
        units_done=task.units_done,
        units_total=task.units_total,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )


def _to_task(row: AnalysisJobTaskRow) -> JobTask:
    return JobTask(
        key=TaskKey(row.key),
        state=TaskState(row.state),
        units_done=row.units_done,
        units_total=row.units_total,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )
