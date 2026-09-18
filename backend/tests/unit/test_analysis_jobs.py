"""Phase 8.1 — analysis job domain types and legal state transitions (pure)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from career_assistant.domain.jobs import (
    AnalysisJob,
    JobError,
    JobKind,
    JobStage,
    JobState,
    RoleStatus,
    mark_failed,
    mark_running,
    mark_stage,
    mark_succeeded,
    new_role_analysis_job,
    recover_stale_running,
)


FIXED_NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def test_new_role_analysis_job_starts_queued_without_stage() -> None:
    job = new_role_analysis_job(
        job_id="job-1",
        workspace_id="ws-1",
        role_id="role-1",
        created_at=FIXED_NOW,
    )
    assert job.kind is JobKind.ROLE_ANALYSIS
    assert job.state is JobState.QUEUED
    assert job.stage is None
    assert job.started_at is None
    assert job.finished_at is None
    assert job.error is None
    assert job.role_id == "role-1"


def test_queued_job_may_start_running_and_advance_stages() -> None:
    job = new_role_analysis_job(
        job_id="job-1",
        workspace_id="ws-1",
        role_id="role-1",
        created_at=FIXED_NOW,
    )
    running = mark_running(job, at=FIXED_NOW + timedelta(seconds=1))
    assert running.state is JobState.RUNNING
    assert running.started_at == FIXED_NOW + timedelta(seconds=1)

    extracting = mark_stage(running, JobStage.EXTRACTING_REQUIREMENTS)
    assert extracting.stage is JobStage.EXTRACTING_REQUIREMENTS
    assert extracting.state is JobState.RUNNING


def test_running_job_may_succeed_and_clear_error() -> None:
    job = mark_running(
        new_role_analysis_job(
            job_id="job-1",
            workspace_id="ws-1",
            role_id="role-1",
            created_at=FIXED_NOW,
        ),
        at=FIXED_NOW,
    )
    job = mark_stage(job, JobStage.SCORING)
    done = mark_succeeded(job, at=FIXED_NOW + timedelta(minutes=1))
    assert done.state is JobState.SUCCEEDED
    assert done.finished_at == FIXED_NOW + timedelta(minutes=1)
    assert done.error is None
    assert done.stage is JobStage.SCORING


def test_running_job_may_fail_with_stage_and_safe_error() -> None:
    job = mark_stage(
        mark_running(
            new_role_analysis_job(
                job_id="job-1",
                workspace_id="ws-1",
                role_id="role-1",
                created_at=FIXED_NOW,
            ),
            at=FIXED_NOW,
        ),
        JobStage.EXTRACTING_CLAIMS,
    )
    failed = mark_failed(
        job,
        at=FIXED_NOW + timedelta(seconds=30),
        error=JobError(code="extraction_failed", message="Claim extraction failed."),
    )
    assert failed.state is JobState.FAILED
    assert failed.stage is JobStage.EXTRACTING_CLAIMS
    assert failed.error is not None
    assert failed.error.code == "extraction_failed"
    assert failed.finished_at == FIXED_NOW + timedelta(seconds=30)


def test_illegal_transitions_are_rejected() -> None:
    queued = new_role_analysis_job(
        job_id="job-1",
        workspace_id="ws-1",
        role_id="role-1",
        created_at=FIXED_NOW,
    )
    with pytest.raises(ValueError):
        mark_succeeded(queued, at=FIXED_NOW)
    with pytest.raises(ValueError):
        mark_stage(queued, JobStage.PARSING)

    succeeded = mark_succeeded(
        mark_running(queued, at=FIXED_NOW),
        at=FIXED_NOW + timedelta(seconds=1),
    )
    with pytest.raises(ValueError):
        mark_running(succeeded, at=FIXED_NOW + timedelta(seconds=2))
    with pytest.raises(ValueError):
        mark_failed(
            succeeded,
            at=FIXED_NOW + timedelta(seconds=2),
            error=JobError(code="x", message="y"),
        )


def test_stale_running_job_is_failed_or_requeued_by_policy() -> None:
    started = FIXED_NOW - timedelta(minutes=30)
    stale = AnalysisJob(
        id="job-1",
        workspace_id="ws-1",
        role_id="role-1",
        kind=JobKind.ROLE_ANALYSIS,
        state=JobState.RUNNING,
        stage=JobStage.MAPPING,
        started_at=started,
        finished_at=None,
        error=None,
        created_at=started,
    )
    # Past timeout → fail with a safe restart reason (do not leave permanently running).
    recovered = recover_stale_running(
        stale,
        now=FIXED_NOW,
        running_timeout=timedelta(minutes=10),
    )
    assert recovered.state is JobState.FAILED
    assert recovered.error is not None
    assert recovered.error.code == "stale_running"
    assert recovered.finished_at == FIXED_NOW

    fresh = AnalysisJob(
        id="job-2",
        workspace_id="ws-1",
        role_id="role-2",
        kind=JobKind.ROLE_ANALYSIS,
        state=JobState.RUNNING,
        stage=JobStage.PARSING,
        started_at=FIXED_NOW - timedelta(minutes=2),
        finished_at=None,
        error=None,
        created_at=FIXED_NOW - timedelta(minutes=2),
    )
    still_running = recover_stale_running(
        fresh,
        now=FIXED_NOW,
        running_timeout=timedelta(minutes=10),
    )
    assert still_running.state is JobState.RUNNING


def test_role_status_values_match_product_contract() -> None:
    assert RoleStatus.ANALYSING == "analysing"
    assert RoleStatus.READY == "ready"
    assert RoleStatus.FAILED == "failed"


def test_job_error_rejects_empty_safe_message() -> None:
    with pytest.raises(ValueError):
        JobError(code="extraction_failed", message="  ")
