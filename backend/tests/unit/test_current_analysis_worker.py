"""The worker always invokes the current chunk and verdict analysis."""

from datetime import UTC, datetime
from unittest.mock import Mock

from career_assistant.adapters.persistence.analysis_worker import SqlAnalysisWorker
from career_assistant.domain.jobs import AnalysisJob, new_role_analysis_job


def test_worker_uses_current_analysis_without_reading_workspace_selector() -> None:
    worker = SqlAnalysisWorker(Mock())
    job = new_role_analysis_job(
        job_id="job",
        workspace_id="ws",
        role_id="role",
        created_at=datetime.now(UTC),
    )
    worker._v2 = Mock()
    worker._v2.run.return_value = job
    assert worker.complete(job) is job
    worker._v2.run.assert_called_once_with(job)
    worker._uow_factory.assert_not_called()


def test_worker_overlaps_independent_jobs_with_the_configured_thread_limit() -> None:
    import threading

    stop = threading.Event()
    barrier = threading.Barrier(2, timeout=3)
    worker = SqlAnalysisWorker(Mock(), max_concurrent=2)
    jobs = tuple(
        new_role_analysis_job(
            job_id=f"job-{index}",
            workspace_id="ws",
            role_id=f"role-{index}",
            created_at=datetime.now(UTC),
        )
        for index in range(2)
    )
    worker.startup = Mock()
    worker.claim_next = Mock(side_effect=[*jobs, None])

    def complete(job: AnalysisJob) -> AnalysisJob:
        barrier.wait()
        stop.set()
        return job

    worker.complete = Mock(side_effect=complete)
    thread = threading.Thread(target=worker.run_forever, args=(stop,))
    thread.start()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert worker.complete.call_count == 2
