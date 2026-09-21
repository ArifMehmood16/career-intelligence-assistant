"""SQL-backed CvStore — production persistence for the CV paste lifecycle."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.documents.cv import CvView, StoredCv
from career_assistant.application.ports.persistence import NewDocument, StoredDocument
from career_assistant.domain.documents import Page, Span
from career_assistant.domain.jobs import (
    JobError,
    JobState,
    RoleStatus,
    mark_failed,
    mark_running,
)
from career_assistant.logconfig import log_event

_log = logging.getLogger(__name__)


class SqlCvStore:
    """CvStore over SqlUnitOfWork. Each method opens its own unit of work."""

    def __init__(self, uow_factory: Callable[[], SqlUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def get_active(self, workspace_id: str) -> StoredCv | None:
        with self._uow_factory() as uow:
            document = uow.documents.get_active_cv(workspace_id)
            if document is None:
                return None
            spans = uow.documents.list_spans(workspace_id, document.id)
            return _to_stored_cv(document, spans)

    def replace(self, workspace_id: str, document: NewDocument) -> StoredCv:
        now = datetime.now(UTC)
        with self._uow_factory() as uow:
            uow.workspaces.ensure(workspace_id)
            stored = uow.documents.replace_cv(workspace_id, document)
            roles = uow.roles.list_for_workspace(workspace_id)
            job_ids = tuple(str(uuid.uuid4()) for _ in roles)
            assigned: tuple[str, ...] = ()
            if job_ids:
                assigned = uow.jobs.enqueue_reanalysis_for_workspace(
                    workspace_id=workspace_id,
                    job_ids=job_ids,
                    created_at=now,
                )
            spans = uow.documents.list_spans(workspace_id, stored.id)
            uow.commit()
            log_event(
                _log,
                "sql.cv.replace",
                document_id=stored.id,
                reanalysis_jobs=len(assigned),
            )
            return _to_stored_cv(stored, spans, reanalysis_job_ids=assigned)

    def delete_active(self, workspace_id: str) -> None:
        now = datetime.now(UTC)
        with self._uow_factory() as uow:
            document = uow.documents.get_active_cv(workspace_id)
            if document is None:
                return
            for role in uow.roles.list_for_workspace(workspace_id):
                active = uow.jobs.active_for_role(workspace_id, role.id)
                if active is not None:
                    running = (
                        active
                        if active.state is JobState.RUNNING
                        else mark_running(active, at=now)
                    )
                    uow.jobs.save(
                        mark_failed(
                            running,
                            at=now,
                            error=JobError(
                                code="cv_deleted",
                                message="The CV was deleted before analysis finished.",
                            ),
                        )
                    )
                uow.roles.set_status(workspace_id, role.id, RoleStatus.FAILED)
            uow.documents.hard_delete(workspace_id, document.id)
            uow.commit()
            log_event(_log, "sql.cv.delete", document_id=document.id)

    def get_span(
        self, workspace_id: str, span_id: str
    ) -> tuple[Span, tuple[Page, ...]] | None:
        active = self.get_active(workspace_id)
        if active is None:
            return None
        for span in active.spans:
            if span.id == span_id:
                return span, active.pages
        return None


def _to_stored_cv(
    document: StoredDocument,
    spans: tuple[Span, ...],
    *,
    reanalysis_job_ids: tuple[str, ...] = (),
) -> StoredCv:
    pages = (
        Page(
            document_id=document.id,
            page_number=1,
            text=document.normalised_text,
        ),
    )
    parsed_at = document.updated_at
    if parsed_at.tzinfo is None:
        parsed_at = parsed_at.replace(tzinfo=UTC)
    return StoredCv(
        view=CvView(
            id=document.id,
            filename=document.filename,
            page_count=document.page_count,
            parsed_at=parsed_at,
            reanalysis_job_ids=reanalysis_job_ids,
        ),
        spans=spans,
        pages=pages,
        normalised_text=document.normalised_text,
        original_bytes=document.original_bytes,
        media_type=document.media_type,
    )
