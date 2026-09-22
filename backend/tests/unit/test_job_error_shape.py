"""PLAN 13D.6e — job errors keep the documented {code, message} shape."""

from __future__ import annotations

from datetime import UTC, datetime

from career_assistant.adapters.persistence.role_store import _job_view
from career_assistant.domain.jobs import (
    AnalysisJob,
    JobError,
    JobKind,
    JobState,
)


def test_job_view_exposes_structured_error_code_and_message() -> None:
    job = AnalysisJob(
        id="job-1",
        workspace_id="ws-1",
        role_id="role-1",
        kind=JobKind.ROLE_ANALYSIS,
        state=JobState.FAILED,
        stage=None,
        started_at=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
        finished_at=datetime(2026, 9, 18, 12, 1, tzinfo=UTC),
        error=JobError(
            code="assessment_incomplete",
            message=(
                "Analysis did not assess every scoreable requirement. "
                "This is not a fit score."
            ),
        ),
        created_at=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
    )

    view = _job_view(job)

    assert view.error is not None
    assert view.error.code == "assessment_incomplete"
    assert "not a fit score" in view.error.message
    assert "assessment_incomplete:" not in view.error.message
