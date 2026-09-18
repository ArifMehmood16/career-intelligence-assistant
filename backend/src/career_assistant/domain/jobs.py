"""Analysis job lifecycle — pure domain transitions, no I/O."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum


class JobKind(StrEnum):
    ROLE_ANALYSIS = "role_analysis"
    CV_PARSE = "cv_parse"
    REINDEX = "reindex"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobStage(StrEnum):
    PARSING = "parsing"
    EXTRACTING_REQUIREMENTS = "extracting_requirements"
    EXTRACTING_CLAIMS = "extracting_claims"
    MAPPING = "mapping"
    SCORING = "scoring"


class RoleStatus(StrEnum):
    ANALYSING = "analysing"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class JobError:
    code: str
    message: str

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("job error code must be non-empty")
        if not self.message.strip():
            raise ValueError("job error message must be non-empty")


@dataclass(frozen=True, slots=True)
class AnalysisJob:
    id: str
    workspace_id: str
    role_id: str
    kind: JobKind
    state: JobState
    stage: JobStage | None
    started_at: datetime | None
    finished_at: datetime | None
    error: JobError | None
    created_at: datetime


def new_role_analysis_job(
    *,
    job_id: str,
    workspace_id: str,
    role_id: str,
    created_at: datetime,
) -> AnalysisJob:
    return AnalysisJob(
        id=job_id,
        workspace_id=workspace_id,
        role_id=role_id,
        kind=JobKind.ROLE_ANALYSIS,
        state=JobState.QUEUED,
        stage=None,
        started_at=None,
        finished_at=None,
        error=None,
        created_at=created_at,
    )


def mark_running(job: AnalysisJob, *, at: datetime) -> AnalysisJob:
    if job.state is not JobState.QUEUED:
        raise ValueError(f"cannot start job in state {job.state}")
    return replace(
        job,
        state=JobState.RUNNING,
        started_at=at,
        finished_at=None,
        error=None,
    )


def mark_stage(job: AnalysisJob, stage: JobStage) -> AnalysisJob:
    if job.state is not JobState.RUNNING:
        raise ValueError(f"cannot set stage on job in state {job.state}")
    return replace(job, stage=stage)


def mark_succeeded(job: AnalysisJob, *, at: datetime) -> AnalysisJob:
    if job.state is not JobState.RUNNING:
        raise ValueError(f"cannot succeed job in state {job.state}")
    return replace(
        job,
        state=JobState.SUCCEEDED,
        finished_at=at,
        error=None,
    )


def mark_failed(job: AnalysisJob, *, at: datetime, error: JobError) -> AnalysisJob:
    if job.state is not JobState.RUNNING:
        raise ValueError(f"cannot fail job in state {job.state}")
    return replace(
        job,
        state=JobState.FAILED,
        finished_at=at,
        error=error,
    )


def recover_stale_running(
    job: AnalysisJob,
    *,
    now: datetime,
    running_timeout: timedelta,
) -> AnalysisJob:
    """Deterministic restart policy: stale running jobs fail; fresh ones stay."""
    if job.state is not JobState.RUNNING:
        return job
    if job.started_at is None:
        return mark_failed(
            job,
            at=now,
            error=JobError(
                code="stale_running",
                message="Analysis did not finish before the process stopped.",
            ),
        )
    if now - job.started_at >= running_timeout:
        return mark_failed(
            job,
            at=now,
            error=JobError(
                code="stale_running",
                message="Analysis did not finish before the process stopped.",
            ),
        )
    return job
