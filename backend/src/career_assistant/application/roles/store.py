"""In-memory role and job store for hermetic API tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from career_assistant.application.documents.cv import CvStore
from career_assistant.application.roles.hermetic_analysis import (
    AnalysisBundle,
    analyse_hermetic,
    band_label,
    count_statuses,
)
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
    description: str = ""


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
    analyses: dict[str, dict[str, AnalysisBundle]] = field(default_factory=dict)
    role_job: dict[str, dict[str, str]] = field(default_factory=dict)

    def create_role(
        self,
        *,
        workspace_id: str,
        title: str,
        company: str,
        description: str,
    ) -> tuple[RoleView, JobView]:
        cv = self.cv_store.get_active(workspace_id)
        if cv is None:
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
        role_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        bundle = analyse_hermetic(
            cv_text=cv.normalised_text,
            cv_document_id=cv.view.id,
            jd_text=description,
        )
        role = RoleView(
            id=role_id,
            title=title,
            company=company,
            fit_score=int(round(bundle.explanation.score)),
            band_label=band_label(bundle.explanation.band),
            counts=count_statuses(bundle.mappings),
            status="ready",
            updated_at=now,
            description=description,
        )
        job = JobView(
            id=job_id,
            kind=JobKind.ROLE_ANALYSIS.value,
            state=JobState.SUCCEEDED.value,
            stage="scoring",
            started_at=now,
            finished_at=now,
            error=None,
        )
        self.roles.setdefault(workspace_id, {})[role.id] = role
        self.jobs.setdefault(workspace_id, {})[job.id] = job
        self.analyses.setdefault(workspace_id, {})[role.id] = bundle
        self.role_job.setdefault(workspace_id, {})[role.id] = job.id
        return role, job

    def list_roles(self, workspace_id: str) -> tuple[RoleView, ...]:
        return tuple(self.roles.get(workspace_id, {}).values())

    def get_role(self, workspace_id: str, role_id: str) -> RoleView | None:
        return self.roles.get(workspace_id, {}).get(role_id)

    def get_job(self, workspace_id: str, job_id: str) -> JobView | None:
        return self.jobs.get(workspace_id, {}).get(job_id)

    def require_analysis(self, workspace_id: str, role_id: str) -> AnalysisBundle:
        role = self.get_role(workspace_id, role_id)
        if role is None:
            raise RoleOperationRejected(
                "role_not_found", "No role with that id.", status_code=404
            )
        if role.status != "ready":
            raise RoleOperationRejected(
                "analysis_incomplete",
                "Analysis has not finished for this role.",
                status_code=409,
            )
        bundle = self.analyses.get(workspace_id, {}).get(role_id)
        if bundle is None:
            raise RoleOperationRejected(
                "analysis_incomplete",
                "Analysis has not finished for this role.",
                status_code=409,
            )
        return bundle

    def ranked(
        self, workspace_id: str
    ) -> tuple[tuple[RoleView, int, bool, tuple[str, ...]], ...]:
        roles = sorted(
            self.list_roles(workspace_id),
            key=lambda role: (-role.fit_score, role.title, role.id),
        )
        out: list[tuple[RoleView, int, bool, tuple[str, ...]]] = []
        for index, role in enumerate(roles, start=1):
            tied = False
            if index > 1 and roles[index - 2].fit_score == role.fit_score:
                tied = True
                prev = out[-1]
                out[-1] = (prev[0], prev[1], True, prev[3])
            because = tuple(
                m.requirement_id
                for m in self.analyses[workspace_id][role.id].mappings
                if m.status.value == "met"
            )[:3]
            # Prefer requirement texts for "because".
            reqs = {
                r.id: r.text for r in self.analyses[workspace_id][role.id].requirements
            }
            because_texts = tuple(reqs[rid] for rid in because if rid in reqs)
            out.append((role, index, tied, because_texts))
        return tuple(out)
