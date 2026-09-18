"""SQLAlchemy repositories for roles, analysis jobs and published results."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from career_assistant.adapters.persistence.models import (
    AnalysisJobRow,
    ClaimRow,
    ClaimSpanRow,
    MappingRow,
    MappingSpanRow,
    RequirementRow,
    RoleRow,
    ScoreExplanationRow,
)
from career_assistant.application.ports.persistence import RoleRecord
from career_assistant.domain.claims import Claim
from career_assistant.domain.jobs import (
    AnalysisJob,
    JobError,
    JobKind,
    JobStage,
    JobState,
    RoleStatus,
    new_role_analysis_job,
)
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoreExplanation


def _as_uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def _to_role(row: RoleRow) -> RoleRecord:
    return RoleRecord(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        title=row.title,
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


def _explanation_payload(explanation: ScoreExplanation) -> dict[str, object]:
    return {
        "score": explanation.score,
        "band": explanation.band,
        "denominator": explanation.denominator,
        "numerator": explanation.numerator,
        "components": [
            {
                "requirement_id": c.requirement_id,
                "must_have": c.must_have,
                "status": c.status.value,
                "weight": c.weight,
                "status_factor": c.status_factor,
                "recency_factor": c.recency_factor,
                "contribution": c.contribution,
            }
            for c in explanation.components
        ],
    }


class SqlRoleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        workspace_id: str,
        role_id: str,
        title: str,
        job_description_document_id: str,
        status: RoleStatus,
    ) -> RoleRecord:
        row = RoleRow(
            id=_as_uuid(role_id),
            workspace_id=_as_uuid(workspace_id),
            title=title,
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
            self._roles.set_status(workspace_id, role.id, RoleStatus.ANALYSING)
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

    def publish(
        self,
        *,
        workspace_id: str,
        role_id: str,
        analysis_version: int,
        cv_document_id: str,
        requirements: tuple[Requirement, ...],
        claims: tuple[Claim, ...],
        mappings: tuple[RequirementMapping, ...],
        explanation: ScoreExplanation,
        job: AnalysisJob,
    ) -> None:
        wid = _as_uuid(workspace_id)
        rid = _as_uuid(role_id)
        # Replace any prior rows for this version (idempotent republish).
        self._delete_analysis_rows(wid, rid, analysis_version)

        for req in requirements:
            self._session.add(
                RequirementRow(
                    id=_as_uuid(req.id),
                    workspace_id=wid,
                    role_id=rid,
                    text=req.text,
                    competency=req.competency,
                    must_have=req.must_have,
                    source_span_id=_as_uuid(req.source_span_id),
                    extraction_confidence=req.extraction_confidence,
                    is_vague=req.is_vague,
                    analysis_version=analysis_version,
                )
            )

        for claim in claims:
            claim_id = _as_uuid(claim.id)
            self._session.add(
                ClaimRow(
                    id=claim_id,
                    workspace_id=wid,
                    document_id=_as_uuid(cv_document_id),
                    competency=claim.competency,
                    context=claim.context,
                    duration_signal=claim.duration_signal,
                    recency_signal=claim.recency_signal,
                )
            )
            for span_id in claim.source_span_ids:
                self._session.add(
                    ClaimSpanRow(
                        workspace_id=wid,
                        claim_id=claim_id,
                        span_id=_as_uuid(span_id),
                    )
                )

        self._session.flush()

        for mapping in mappings:
            mapping_id = uuid.uuid4()
            self._session.add(
                MappingRow(
                    id=mapping_id,
                    workspace_id=wid,
                    role_id=rid,
                    requirement_id=_as_uuid(mapping.requirement_id),
                    status=mapping.status.value,
                    reason_code=mapping.reason_code.value,
                    analysis_version=analysis_version,
                    invalidated=False,
                )
            )
            for span_id in mapping.justifying_span_ids:
                self._session.add(
                    MappingSpanRow(
                        workspace_id=wid,
                        mapping_id=mapping_id,
                        span_id=_as_uuid(span_id),
                    )
                )

        self._session.add(
            ScoreExplanationRow(
                id=uuid.uuid4(),
                workspace_id=wid,
                role_id=rid,
                analysis_version=analysis_version,
                score=explanation.score,
                band=explanation.band,
                explanation=_explanation_payload(explanation),
                invalidated=False,
            )
        )
        self._jobs.save(job)
        self._roles.set_status(workspace_id, role_id, RoleStatus.READY)
        self._session.flush()

    def fail_job(
        self,
        *,
        workspace_id: str,
        role_id: str,
        job: AnalysisJob,
    ) -> None:
        self._delete_analysis_rows(
            _as_uuid(workspace_id),
            _as_uuid(role_id),
            analysis_version=None,
        )
        self._jobs.save(job)
        self._roles.set_status(workspace_id, role_id, RoleStatus.FAILED)
        self._session.flush()

    def list_mappings(
        self, workspace_id: str, role_id: str
    ) -> tuple[RequirementMapping, ...]:
        rows = self._session.scalars(
            select(MappingRow).where(
                MappingRow.workspace_id == _as_uuid(workspace_id),
                MappingRow.role_id == _as_uuid(role_id),
                MappingRow.invalidated.is_(False),
            )
        ).all()
        results: list[RequirementMapping] = []
        for row in rows:
            span_ids = tuple(
                str(span.span_id)
                for span in self._session.scalars(
                    select(MappingSpanRow).where(MappingSpanRow.mapping_id == row.id)
                ).all()
            )
            results.append(
                RequirementMapping(
                    requirement_id=str(row.requirement_id),
                    status=MappingStatus(row.status),
                    reason_code=MappingReason(row.reason_code),
                    justifying_span_ids=span_ids,
                    justifying_claim_ids=(),
                )
            )
        return tuple(results)

    def _delete_analysis_rows(
        self,
        workspace_id: uuid.UUID,
        role_id: uuid.UUID,
        analysis_version: int | None,
    ) -> None:
        mapping_filter = [
            MappingRow.workspace_id == workspace_id,
            MappingRow.role_id == role_id,
        ]
        req_filter = [
            RequirementRow.workspace_id == workspace_id,
            RequirementRow.role_id == role_id,
        ]
        score_filter = [
            ScoreExplanationRow.workspace_id == workspace_id,
            ScoreExplanationRow.role_id == role_id,
        ]
        if analysis_version is not None:
            mapping_filter.append(MappingRow.analysis_version == analysis_version)
            req_filter.append(RequirementRow.analysis_version == analysis_version)
            score_filter.append(
                ScoreExplanationRow.analysis_version == analysis_version
            )

        mapping_ids = self._session.scalars(
            select(MappingRow.id).where(*mapping_filter)
        ).all()
        if mapping_ids:
            self._session.execute(
                delete(MappingSpanRow).where(MappingSpanRow.mapping_id.in_(mapping_ids))
            )
            self._session.execute(delete(MappingRow).where(*mapping_filter))
        self._session.execute(delete(RequirementRow).where(*req_filter))
        self._session.execute(delete(ScoreExplanationRow).where(*score_filter))
        # Claims are CV-scoped; discard claim_spans + claims for this workspace CV
        # only when discarding partials for a failed role analysis with no version.
        if analysis_version is None:
            claim_ids = self._session.scalars(
                select(ClaimRow.id).where(ClaimRow.workspace_id == workspace_id)
            ).all()
            if claim_ids:
                self._session.execute(
                    delete(ClaimSpanRow).where(ClaimSpanRow.claim_id.in_(claim_ids))
                )
                self._session.execute(
                    delete(ClaimRow).where(ClaimRow.workspace_id == workspace_id)
                )
        self._session.flush()
