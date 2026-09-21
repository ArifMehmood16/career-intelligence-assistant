"""In-memory role and job store for hermetic API tests."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from career_assistant.application.documents.cv import CvStore
from career_assistant.application.ports.errors import EgressNotPermittedError
from career_assistant.application.ports.extraction import (
    ClaimExtractionPort,
    RequirementExtractionPort,
)
from career_assistant.application.roles.hermetic_analysis import (
    AnalysisBundle,
    analyse_hermetic,
    band_label,
    count_statuses,
)
from career_assistant.domain.documents import Page, Span
from career_assistant.domain.jobs import JobKind, JobState

ExtractorFactory = Callable[
    [str], tuple[RequirementExtractionPort, ClaimExtractionPort]
]


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
    extractor_factory: ExtractorFactory | None = None
    roles: dict[str, dict[str, RoleView]] = field(default_factory=dict)
    jobs: dict[str, dict[str, JobView]] = field(default_factory=dict)
    analyses: dict[str, dict[str, AnalysisBundle]] = field(default_factory=dict)
    role_job: dict[str, dict[str, str]] = field(default_factory=dict)
    cover_letters: dict[str, dict[str, list[object]]] = field(default_factory=dict)
    bullet_drafts: dict[str, dict[str, list[object]]] = field(default_factory=dict)

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
        bundle = self._analyse(
            workspace_id,
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

    def get_span(
        self, workspace_id: str, span_id: str
    ) -> tuple[Span, tuple[Page, ...]] | None:
        for role_id, bundle in self.analyses.get(workspace_id, {}).items():
            role = self.roles.get(workspace_id, {}).get(role_id)
            if role is None:
                continue
            for span in bundle.jd_spans:
                if span.id == span_id:
                    pages = (
                        Page(
                            document_id=bundle.jd_document_id,
                            page_number=1,
                            text=role.description,
                        ),
                    )
                    return span, pages
            for span in bundle.cv_claim_spans:
                if span.id != span_id:
                    continue
                cv = self.cv_store.get_active(workspace_id)
                if cv is None:
                    return None
                return span, cv.pages
        return None

    def get_job(self, workspace_id: str, job_id: str) -> JobView | None:
        return self.jobs.get(workspace_id, {}).get(job_id)

    def delete_role(self, workspace_id: str, role_id: str) -> None:
        role = self.get_role(workspace_id, role_id)
        if role is None:
            raise RoleOperationRejected(
                "role_not_found", "No role with that id.", status_code=404
            )
        job_id = self.role_job.get(workspace_id, {}).pop(role_id, None)
        self.roles.get(workspace_id, {}).pop(role_id, None)
        self.analyses.get(workspace_id, {}).pop(role_id, None)
        self.cover_letters.get(workspace_id, {}).pop(role_id, None)
        self.bullet_drafts.get(workspace_id, {}).pop(role_id, None)
        if job_id is not None:
            self.jobs.get(workspace_id, {}).pop(job_id, None)

    def reanalyse(self, workspace_id: str, role_id: str) -> tuple[RoleView, JobView]:
        role = self.get_role(workspace_id, role_id)
        if role is None:
            raise RoleOperationRejected(
                "role_not_found", "No role with that id.", status_code=404
            )
        cv = self.cv_store.get_active(workspace_id)
        if cv is None:
            raise RoleOperationRejected(
                "cv_required",
                "Upload a CV before reanalysing a role.",
                status_code=409,
            )
        now = datetime.now(UTC)
        job_id = str(uuid.uuid4())
        bundle = self._analyse(
            workspace_id,
            cv_text=cv.normalised_text,
            cv_document_id=cv.view.id,
            jd_text=role.description,
        )
        updated = RoleView(
            id=role.id,
            title=role.title,
            company=role.company,
            fit_score=int(round(bundle.explanation.score)),
            band_label=band_label(bundle.explanation.band),
            counts=count_statuses(bundle.mappings),
            status="ready",
            updated_at=now,
            description=role.description,
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
        self.roles[workspace_id][role_id] = updated
        self.jobs.setdefault(workspace_id, {})[job.id] = job
        self.analyses.setdefault(workspace_id, {})[role_id] = bundle
        self.role_job.setdefault(workspace_id, {})[role_id] = job.id
        return updated, job

    def mark_incomplete(self, workspace_id: str, role_id: str) -> None:
        """Test helper: leave the role analysing with no finished analysis."""
        role = self.get_role(workspace_id, role_id)
        if role is None:
            raise RoleOperationRejected(
                "role_not_found", "No role with that id.", status_code=404
            )
        self.roles[workspace_id][role_id] = RoleView(
            id=role.id,
            title=role.title,
            company=role.company,
            fit_score=0,
            band_label="Not scored yet",
            counts={"met": 0, "partial": 0, "missing": 0},
            status="analysing",
            updated_at=datetime.now(UTC),
            description=role.description,
        )
        self.analyses.get(workspace_id, {}).pop(role_id, None)

    def save_cover_letter(self, workspace_id: str, role_id: str, draft: object) -> None:
        self.cover_letters.setdefault(workspace_id, {}).setdefault(role_id, []).append(
            draft
        )

    def list_cover_letters(self, workspace_id: str, role_id: str) -> tuple[object, ...]:
        if self.get_role(workspace_id, role_id) is None:
            raise RoleOperationRejected(
                "role_not_found", "No role with that id.", status_code=404
            )
        return tuple(self.cover_letters.get(workspace_id, {}).get(role_id, []))

    def save_bullet_draft(self, workspace_id: str, role_id: str, draft: object) -> None:
        self.bullet_drafts.setdefault(workspace_id, {}).setdefault(role_id, []).append(
            draft
        )

    def list_bullet_drafts(self, workspace_id: str, role_id: str) -> tuple[object, ...]:
        if self.get_role(workspace_id, role_id) is None:
            raise RoleOperationRejected(
                "role_not_found", "No role with that id.", status_code=404
            )
        return tuple(self.bullet_drafts.get(workspace_id, {}).get(role_id, []))

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

    def _analyse(
        self,
        workspace_id: str,
        *,
        cv_text: str,
        cv_document_id: str,
        jd_text: str,
    ) -> AnalysisBundle:
        requirement_extractor = None
        claim_extractor = None
        if self.extractor_factory is not None:
            try:
                requirement_extractor, claim_extractor = self.extractor_factory(
                    workspace_id
                )
            except EgressNotPermittedError as exc:
                raise RoleOperationRejected(
                    "egress_not_permitted",
                    "Hosted provider is not permitted.",
                    status_code=403,
                ) from exc
        return analyse_hermetic(
            cv_text=cv_text,
            cv_document_id=cv_document_id,
            jd_text=jd_text,
            requirement_extractor=requirement_extractor,
            claim_extractor=claim_extractor,
        )

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
