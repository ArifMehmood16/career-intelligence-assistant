"""In-memory role and job store for hermetic API tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from career_assistant.application.documents.cv import CvStore
from career_assistant.domain.jobs import JobKind, JobState


class RoleOperationRejected(Exception):
    def __init__(self, code: str, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class RoleView:
    id: str
    title: str
    company: str
    fit_score: int
    band_label: str
    counts: dict[str, int]
    status: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class JobView:
    id: str
    kind: str
    state: str
    stage: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None


@dataclass
class InMemoryRoleStore:
    cv_store: CvStore
    roles: dict[str, dict[str, RoleView]] = field(default_factory=dict)
    jobs: dict[str, dict[str, JobView]] = field(default_factory=dict)

    def create_role(
        self,
        *,
        workspace_id: str,
        title: str,
        company: str,
        description: str,
    ) -> tuple[RoleView, JobView]:
        if self.cv_store.get_active(workspace_id) is None:
            raise RoleOperationRejected(
                "cv_required",
                "Upload a CV before adding a role.",
                status_code=409,
            )
        if not description.strip():
            raise RoleOperationRejected(
                "validation_failed",
                "Role description is required.",
                status_code=422,
            )
        now = datetime.now(UTC)
        role = RoleView(
            id=str(uuid.uuid4()),
            title=title,
            company=company,
            fit_score=0,
            band_label="Not scored yet",
            counts={"met": 0, "partial": 0, "missing": 0},
            status="analysing",
            updated_at=now,
        )
        job = JobView(
            id=str(uuid.uuid4()),
            kind=JobKind.ROLE_ANALYSIS.value,
            state=JobState.QUEUED.value,
            stage=None,
            started_at=None,
            finished_at=None,
            error=None,
        )
        self.roles.setdefault(workspace_id, {})[role.id] = role
        self.jobs.setdefault(workspace_id, {})[job.id] = job
        return role, job

    def list_roles(self, workspace_id: str) -> tuple[RoleView, ...]:
        return tuple(self.roles.get(workspace_id, {}).values())

    def get_role(self, workspace_id: str, role_id: str) -> RoleView | None:
        return self.roles.get(workspace_id, {}).get(role_id)

    def get_job(self, workspace_id: str, job_id: str) -> JobView | None:
        return self.jobs.get(workspace_id, {}).get(job_id)
