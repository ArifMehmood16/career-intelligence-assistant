"""SQLAlchemy repositories for roles, analysis jobs and published results."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from career_assistant.adapters.persistence.models import (
    AnalysisJobRow,
    RoleRow,
    ScoreExplanationRow,
)
from career_assistant.application.ports.persistence import RoleRecord
from career_assistant.domain.jobs import (
    AnalysisJob,
    JobError,
    JobKind,
    JobStage,
    JobState,
    RoleStatus,
    new_role_analysis_job,
)
from career_assistant.domain.pipeline import PipelineVersion
from career_assistant.domain.reanalysis import resolve_failed_analysis_pointer
from career_assistant.logconfig import log_event

_log = logging.getLogger(__name__)


def _as_uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def _to_role(row: RoleRow) -> RoleRecord:
    return RoleRecord(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        title=row.title,
        company=row.company,
        job_description_document_id=str(row.job_description_document_id),
        analysis_version=row.analysis_version,
        status=RoleStatus(row.status),
        created_at=row.created_at,
    )


def _to_job(row: AnalysisJobRow) -> AnalysisJob:
    error = None
    if row.error_code and row.error_message:
        error = JobError(code=row.error_code, message=row.error_message)
    return AnalysisJob(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        role_id=str(row.role_id),
        kind=JobKind(row.kind),
        state=JobState(row.state),
        stage=JobStage(row.stage) if row.stage else None,
        started_at=row.started_at,
        finished_at=row.finished_at,
        error=error,
        created_at=row.created_at,
    )


def _apply_job(row: AnalysisJobRow, job: AnalysisJob) -> None:
    row.kind = job.kind.value
    row.state = job.state.value
    row.stage = job.stage.value if job.stage else None
    row.started_at = job.started_at
    row.finished_at = job.finished_at
    row.error_code = job.error.code if job.error else None
    row.error_message = job.error.message if job.error else None


class SqlRoleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        workspace_id: str,
        role_id: str,
        title: str,
        company: str,
        job_description_document_id: str,
        status: RoleStatus,
    ) -> RoleRecord:
        row = RoleRow(
            id=_as_uuid(role_id),
            workspace_id=_as_uuid(workspace_id),
            title=title,
            company=company,
            job_description_document_id=_as_uuid(job_description_document_id),
            analysis_version=1,
            status=status.value,
        )
        self._session.add(row)
        self._session.flush()
        return _to_role(row)

    def get(self, workspace_id: str, role_id: str) -> RoleRecord | None:
        row = self._session.scalar(
            select(RoleRow).where(
                RoleRow.workspace_id == _as_uuid(workspace_id),
                RoleRow.id == _as_uuid(role_id),
            )
        )
        return _to_role(row) if row else None

    def list_for_workspace(self, workspace_id: str) -> tuple[RoleRecord, ...]:
        rows = self._session.scalars(
            select(RoleRow)
            .where(RoleRow.workspace_id == _as_uuid(workspace_id))
            .order_by(RoleRow.created_at.asc())
        ).all()
        return tuple(_to_role(row) for row in rows)

    def set_status(
        self, workspace_id: str, role_id: str, status: RoleStatus
    ) -> RoleRecord:
        row = self._session.scalar(
            select(RoleRow).where(
                RoleRow.workspace_id == _as_uuid(workspace_id),
                RoleRow.id == _as_uuid(role_id),
            )
        )
        if row is None:
            raise KeyError(role_id)
        row.status = status.value
        self._session.flush()
        return _to_role(row)

    def set_analysis_pointer(
        self,
        workspace_id: str,
        role_id: str,
        *,
        analysis_version: int,
        status: RoleStatus,
    ) -> RoleRecord:
        row = self._session.scalar(
            select(RoleRow).where(
                RoleRow.workspace_id == _as_uuid(workspace_id),
                RoleRow.id == _as_uuid(role_id),
            )
        )
        if row is None:
            raise KeyError(role_id)
        row.analysis_version = analysis_version
        row.status = status.value
        self._session.flush()
        return _to_role(row)

    def bump_analysis_version(self, workspace_id: str, role_id: str) -> RoleRecord:
        row = self._session.scalar(
            select(RoleRow).where(
                RoleRow.workspace_id == _as_uuid(workspace_id),
                RoleRow.id == _as_uuid(role_id),
            )
        )
        if row is None:
            raise KeyError(role_id)
        row.analysis_version += 1
        row.status = RoleStatus.ANALYSING.value
        self._session.flush()
        return _to_role(row)

    def delete(self, workspace_id: str, role_id: str) -> None:
        row = self._session.scalar(
            select(RoleRow).where(
                RoleRow.workspace_id == _as_uuid(workspace_id),
                RoleRow.id == _as_uuid(role_id),
            )
        )
        if row is None:
            raise KeyError(role_id)
        self._session.delete(row)
        self._session.flush()


class SqlAnalysisJobRepository:
    def __init__(self, session: Session, roles: SqlRoleRepository) -> None:
        self._session = session
        self._roles = roles

    def enqueue(self, job: AnalysisJob) -> AnalysisJob:
        row = AnalysisJobRow(
            id=_as_uuid(job.id),
            workspace_id=_as_uuid(job.workspace_id),
            role_id=_as_uuid(job.role_id),
            kind=job.kind.value,
            state=job.state.value,
            stage=job.stage.value if job.stage else None,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error_code=job.error.code if job.error else None,
            error_message=job.error.message if job.error else None,
            created_at=job.created_at,
        )
        self._session.add(row)
        self._session.flush()
        log_event(
            _log,
            "sql.job.enqueued",
            job_id=job.id,
            role_id=job.role_id,
            state=job.state.value,
        )
        return _to_job(row)

    def enqueue_idempotent(self, job: AnalysisJob) -> AnalysisJob:
        existing = self._session.scalar(
            select(AnalysisJobRow).where(
                AnalysisJobRow.workspace_id == _as_uuid(job.workspace_id),
                AnalysisJobRow.role_id == _as_uuid(job.role_id),
                AnalysisJobRow.state.in_(
                    (JobState.QUEUED.value, JobState.RUNNING.value)
                ),
            )
        )
        if existing is not None:
            return _to_job(existing)
        return self.enqueue(job)

    def get(self, workspace_id: str, job_id: str) -> AnalysisJob | None:
        row = self._session.scalar(
            select(AnalysisJobRow).where(
                AnalysisJobRow.workspace_id == _as_uuid(workspace_id),
                AnalysisJobRow.id == _as_uuid(job_id),
            )
        )
        return _to_job(row) if row else None

    def get_for_update(self, workspace_id: str, job_id: str) -> AnalysisJob | None:
        """Read the job and hold its row lock until this unit of work ends."""
        row = self._session.scalar(
            select(AnalysisJobRow)
            .where(
                AnalysisJobRow.workspace_id == _as_uuid(workspace_id),
                AnalysisJobRow.id == _as_uuid(job_id),
            )
            .with_for_update()
        )
        return _to_job(row) if row else None

    def save(self, job: AnalysisJob) -> AnalysisJob:
        row = self._session.scalar(
            select(AnalysisJobRow).where(
                AnalysisJobRow.workspace_id == _as_uuid(job.workspace_id),
                AnalysisJobRow.id == _as_uuid(job.id),
            )
        )
        if row is None:
            raise KeyError(job.id)
        _apply_job(row, job)
        self._session.flush()
        return _to_job(row)

    def enqueue_reanalysis_for_workspace(
        self,
        *,
        workspace_id: str,
        job_ids: tuple[str, ...],
        created_at: datetime,
    ) -> tuple[str, ...]:
        roles = self._roles.list_for_workspace(workspace_id)
        if len(job_ids) != len(roles):
            raise ValueError("job_ids must match workspace role count")
        assigned: list[str] = []
        for role, job_id in zip(roles, job_ids, strict=True):
            self._roles.bump_analysis_version(workspace_id, role.id)
            active = self._session.scalars(
                select(AnalysisJobRow).where(
                    AnalysisJobRow.workspace_id == _as_uuid(workspace_id),
                    AnalysisJobRow.role_id == _as_uuid(role.id),
                    AnalysisJobRow.state.in_(
                        (JobState.QUEUED.value, JobState.RUNNING.value)
                    ),
                )
            ).all()
            for row in active:
                row.state = JobState.FAILED.value
                row.error_code = "superseded"
                row.error_message = "Superseded by CV replacement re-analysis."
                row.finished_at = created_at
            job = new_role_analysis_job(
                job_id=job_id,
                workspace_id=workspace_id,
                role_id=role.id,
                created_at=created_at,
            )
            self.enqueue(job)
            assigned.append(job_id)
        self._session.flush()
        return tuple(assigned)

    def set_pipeline_version(
        self, workspace_id: str, job_id: str, version: PipelineVersion
    ) -> None:
        row = self._session.get(AnalysisJobRow, _as_uuid(job_id))
        if row is not None and row.workspace_id == _as_uuid(workspace_id):
            row.pipeline_version = version.value
            self._session.flush()

    def list_queued(self) -> tuple[AnalysisJob, ...]:
        return self._list_by_state(JobState.QUEUED)

    def list_running(self) -> tuple[AnalysisJob, ...]:
        return self._list_by_state(JobState.RUNNING)

    def active_for_role(self, workspace_id: str, role_id: str) -> AnalysisJob | None:
        row = self._session.scalar(
            select(AnalysisJobRow)
            .where(
                AnalysisJobRow.workspace_id == _as_uuid(workspace_id),
                AnalysisJobRow.role_id == _as_uuid(role_id),
                AnalysisJobRow.state.in_(
                    (JobState.QUEUED.value, JobState.RUNNING.value)
                ),
            )
            .order_by(AnalysisJobRow.created_at.asc())
        )
        return _to_job(row) if row is not None else None

    def live_for_workspace(self, workspace_id: str) -> tuple[AnalysisJob, ...]:
        """Queued and running jobs, in the order the worker takes them."""
        rows = self._session.scalars(
            select(AnalysisJobRow)
            .where(
                AnalysisJobRow.workspace_id == _as_uuid(workspace_id),
                AnalysisJobRow.state.in_(
                    (JobState.QUEUED.value, JobState.RUNNING.value)
                ),
            )
            .order_by(AnalysisJobRow.created_at.asc(), AnalysisJobRow.id.asc())
        ).all()
        return tuple(_to_job(row) for row in rows)

    def _list_by_state(self, state: JobState) -> tuple[AnalysisJob, ...]:
        rows = self._session.scalars(
            select(AnalysisJobRow)
            .where(AnalysisJobRow.state == state.value)
            .order_by(AnalysisJobRow.created_at.asc(), AnalysisJobRow.id.asc())
        ).all()
        return tuple(_to_job(row) for row in rows)


class SqlAnalysisResultRepository:
    def __init__(
        self,
        session: Session,
        roles: SqlRoleRepository,
        jobs: SqlAnalysisJobRepository,
    ) -> None:
        self._session = session
        self._roles = roles
        self._jobs = jobs

    def fail_job(
        self,
        *,
        workspace_id: str,
        role_id: str,
        job: AnalysisJob,
    ) -> None:
        role = self._roles.get(workspace_id, role_id)
        version = None if role is None else role.analysis_version
        self._delete_analysis_rows(
            _as_uuid(workspace_id),
            _as_uuid(role_id),
            analysis_version=version,
        )
        # The role status is what the interface shows. Record it even when the
        # job row has gone, or a role sits in `analysing` for ever with no error.
        job_recorded = self._jobs.get(workspace_id, job.id) is not None
        if job_recorded:
            self._jobs.save(job)
        if role is not None and version is not None:
            published = self._published_versions(workspace_id, role_id)
            restore_to, status = resolve_failed_analysis_pointer(
                current_version=version,
                published_versions=published,
            )
            self._roles.set_analysis_pointer(
                workspace_id,
                role_id,
                analysis_version=restore_to,
                status=status,
            )
        else:
            self._roles.set_status(workspace_id, role_id, RoleStatus.FAILED)
        self._session.flush()
        log_event(
            _log,
            "sql.analysis.failed",
            role_id=role_id,
            job_id=job.id,
            code=job.error.code if job.error else "unknown",
            job_recorded=job_recorded,
        )

    def _published_versions(self, workspace_id: str, role_id: str) -> tuple[int, ...]:
        rows = self._session.scalars(
            select(ScoreExplanationRow.analysis_version).where(
                ScoreExplanationRow.workspace_id == _as_uuid(workspace_id),
                ScoreExplanationRow.role_id == _as_uuid(role_id),
            )
        ).all()
        return tuple(int(version) for version in rows)

    def _delete_analysis_rows(
        self,
        workspace_id: uuid.UUID,
        role_id: uuid.UUID,
        analysis_version: int | None,
    ) -> None:
        filters = [
            ScoreExplanationRow.workspace_id == workspace_id,
            ScoreExplanationRow.role_id == role_id,
        ]
        if analysis_version is not None:
            filters.append(ScoreExplanationRow.analysis_version == analysis_version)
        self._session.execute(delete(ScoreExplanationRow).where(*filters))
        self._session.flush()
