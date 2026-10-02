"""Checks the current analysis makes before it writes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from career_assistant.application.ports.errors import JobCancelled
from career_assistant.domain.jobs import LIVE_STATES, AnalysisJob

__all__ = ["JobCancelled", "require_documents", "require_live_job"]


class DocumentReader(Protocol):
    def get(self, workspace_id: str, document_id: str) -> object | None: ...


class JobLocker(Protocol):
    def get_for_update(self, workspace_id: str, job_id: str) -> AnalysisJob | None: ...


def require_live_job(jobs: JobLocker, workspace_id: str, job_id: str) -> AnalysisJob:
    """A deleted or stopped job is a cancellation, not an analysis failure.

    Hard delete removes the role, its job rows and its job description; deleting
    or replacing the CV fails the job while it runs. The worker may already be
    past extraction. Writing then fails a foreign key, or saves the in-memory
    running job over `cv_deleted`. The row stays locked until the caller's
    transaction ends, so a delete cannot land between this check and the write.
    """
    job = jobs.get_for_update(workspace_id, job_id)
    if job is None or job.state not in LIVE_STATES:
        raise JobCancelled(job_id)
    return job


def require_documents(
    documents: DocumentReader,
    workspace_id: str,
    document_ids: Sequence[str],
) -> None:
    """Fail by name when an upload the analysis started from has gone.

    Extraction runs for minutes between reading a document and writing its
    spans, and a replaced or deleted upload takes its row with it. Writing
    anyway raised a foreign-key violation from the driver, which says nothing
    about what happened.
    """
    missing = [
        document_id
        for document_id in document_ids
        if documents.get(workspace_id, document_id) is None
    ]
    if missing:
        raise RuntimeError("documents_changed")
