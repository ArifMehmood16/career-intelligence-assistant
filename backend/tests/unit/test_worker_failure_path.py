"""PLAN 13D.6 — a failing job must not take the worker down with it.

Observed on 2026-09-22: a foreign-key violation on `spans` reached the failure
handler, the handler raised `KeyError` on the job row, and the exception left
`run_forever`. The thread ended, so every later analysis in that process stayed
queued for ever with no error anywhere in the interface.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from types import TracebackType

import pytest

from career_assistant.adapters.persistence.analysis_worker import (
    SqlAnalysisWorker,
    require_documents,
)
from career_assistant.application.analysis.service import StartupRecovery
from career_assistant.domain.jobs import (
    AnalysisJob,
    JobKind,
    JobStage,
    JobState,
)


def _job() -> AnalysisJob:
    at = datetime(2026, 9, 22, tzinfo=UTC)
    return AnalysisJob(
        id="job-1",
        workspace_id="workspace-1",
        role_id="role-1",
        kind=JobKind.ROLE_ANALYSIS,
        state=JobState.RUNNING,
        stage=JobStage.SCORING,
        started_at=at,
        finished_at=None,
        error=None,
        created_at=at,
    )


class _MissingJobs:
    def get(self, workspace_id: str, job_id: str) -> AnalysisJob | None:
        return None


class _RefusingAnalysis:
    def fail_job(self, **kwargs: object) -> None:
        raise KeyError("job-1")


class _BrokenUow:
    """The state the worker was actually in: the job row cannot be written."""

    def __init__(self) -> None:
        self.jobs = _MissingJobs()
        self.analysis = _RefusingAnalysis()
        self.committed = False

    def __enter__(self) -> _BrokenUow:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def commit(self) -> None:
        self.committed = True


class _LoopWorker(SqlAnalysisWorker):
    """Counts loop turns and raises on the first, as the observed job did."""

    def __init__(self, stop: threading.Event) -> None:
        super().__init__(_BrokenUow)  # type: ignore[arg-type]
        self.turns = 0
        self._stop = stop

    def startup(self) -> StartupRecovery:
        return StartupRecovery(failed_job_ids=(), dispatched_job_ids=())

    def process_next(self) -> AnalysisJob | None:
        self.turns += 1
        if self.turns == 1:
            raise RuntimeError("foreign key violation")
        self._stop.set()
        return None


def test_the_worker_keeps_running_after_a_job_fails_to_fail() -> None:
    stop = threading.Event()
    worker = _LoopWorker(stop)

    worker.run_forever(stop, idle_wait_seconds=0.0)

    assert worker.turns >= 2, "the loop ended on the first exception"
    assert stop.is_set()


def test_a_missing_job_row_does_not_escape_the_failure_handler() -> None:
    """The handler records what it can. It never raises into the loop."""
    worker = SqlAnalysisWorker(_BrokenUow)  # type: ignore[arg-type]

    failed = worker._fail(_job(), JobStage.SCORING, RuntimeError("boom"))

    assert failed.state is JobState.FAILED
    assert failed.error is not None
    assert failed.error.code == "scoring_failed"


class _Documents:
    def __init__(self, present: set[str]) -> None:
        self._present = present

    def get(self, workspace_id: str, document_id: str) -> object | None:
        return object() if document_id in self._present else None


def test_a_document_removed_mid_analysis_is_named_not_a_constraint_error() -> None:
    """Extraction takes minutes. The upload it started from can be gone by the end.

    Writing spans against a deleted document raised a foreign-key violation from
    the driver. The write now checks first and says what happened.
    """
    documents = _Documents({"doc-jd"})

    require_documents(documents, "workspace-1", ("doc-jd",))

    with pytest.raises(RuntimeError, match="documents_changed"):
        require_documents(documents, "workspace-1", ("doc-jd", "doc-cv"))
