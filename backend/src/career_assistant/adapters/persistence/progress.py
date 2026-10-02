"""Write an analysis job's progress to its task rows, one commit per change."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from career_assistant.adapters.persistence.job_guards import require_live_job
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.analysis.progress import TrackedProgress
from career_assistant.domain.jobs import AnalysisJob
from career_assistant.domain.pipeline import PipelineVersion
from career_assistant.domain.progress import JobTask, plan_for


def sql_progress(
    uow_factory: Callable[[], SqlUnitOfWork],
    job: AnalysisJob,
    pipeline: PipelineVersion,
    clock: Callable[[], datetime],
) -> TrackedProgress:
    """Progress for one job. A report for a deleted or stopped job cancels it."""

    def write(tasks: tuple[JobTask, ...]) -> None:
        with uow_factory() as uow:
            require_live_job(uow.jobs, job.workspace_id, job.id)
            uow.job_tasks.put(job.workspace_id, job.id, tasks)
            uow.commit()

    return TrackedProgress(plan_for(pipeline), clock=clock, sink=write)
