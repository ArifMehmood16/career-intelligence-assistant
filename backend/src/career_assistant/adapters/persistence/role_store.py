"""SQL-backed role store — hermetic analyse + publish into PostgreSQL."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from career_assistant.adapters.persistence.models import (
    ClaimRow,
    ClaimSpanRow,
    RequirementRow,
    ScoreExplanationRow,
)
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.documents.cv import CvStore
from career_assistant.application.ports.persistence import (
    GeneratedDraftRecord,
    NewDocument,
    NewGeneratedDraft,
    ParseStatus,
    RoleRecord,
)
from career_assistant.application.roles.hermetic_analysis import (
    AnalysisBundle,
    analyse_hermetic,
    band_label,
    count_statuses,
)
from career_assistant.application.roles.store import (
    JobView,
    RoleOperationRejected,
    RoleView,
)
from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.groundedness import GroundednessVerdict
from career_assistant.domain.jobs import (
    JobStage,
    RoleStatus,
    mark_running,
    mark_stage,
    mark_succeeded,
    new_role_analysis_job,
)
from career_assistant.domain.mapping import MappingStatus
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoreComponent, ScoreExplanation


class SqlRoleStore:
    """RoleStore over SqlUnitOfWork. Sync hermetic analyse on create."""

    def __init__(
        self,
        *,
        cv_store: CvStore,
        uow_factory: Callable[[], SqlUnitOfWork],
    ) -> None:
        self.cv_store = cv_store
        self._uow_factory = uow_factory

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

        bundle = analyse_hermetic(
            cv_text=cv.normalised_text,
            cv_document_id=cv.view.id,
            jd_text=description,
        )
        now = datetime.now(UTC)
        role_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        body = description.encode("utf-8")
        jd_document = NewDocument(
            id=bundle.jd_document_id,
            kind=DocumentKind.JOB_DESCRIPTION,
            filename="job-description.txt",
            media_type="text/plain",
            original_bytes=body,
            sha256=hashlib.sha256(body).hexdigest(),
            normalised_text=description,
            parse_status=ParseStatus.PARSED,
            page_count=1,
            character_count=len(description),
            is_active=False,
            spans=bundle.jd_spans,
        )
        queued = new_role_analysis_job(
            job_id=job_id,
            workspace_id=workspace_id,
            role_id=role_id,
            created_at=now,
        )
        terminal = mark_succeeded(
            mark_stage(mark_running(queued, at=now), JobStage.SCORING),
            at=now,
        )

        with self._uow_factory() as uow:
            uow.workspaces.ensure(workspace_id)
            uow.documents.save_admitted(workspace_id, jd_document)
            uow.documents.ensure_spans(workspace_id, cv.view.id, bundle.cv_claim_spans)
            uow.roles.create(
                workspace_id=workspace_id,
                role_id=role_id,
                title=title,
                company=company,
                job_description_document_id=bundle.jd_document_id,
                status=RoleStatus.ANALYSING,
            )
            uow.jobs.enqueue(queued)
            uow.analysis.publish(
                workspace_id=workspace_id,
                role_id=role_id,
                analysis_version=1,
                cv_document_id=cv.view.id,
                requirements=bundle.requirements,
                claims=bundle.claims,
                mappings=bundle.mappings,
                explanation=bundle.explanation,
                job=terminal,
            )
            uow.commit()

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
            kind=terminal.kind.value,
            state=terminal.state.value,
            stage=terminal.stage.value if terminal.stage else None,
            started_at=terminal.started_at,
            finished_at=terminal.finished_at,
            error=None,
        )
        return role, job

    def delete_role(self, workspace_id: str, role_id: str) -> None:
        with self._uow_factory() as uow:
            record = uow.roles.get(workspace_id, role_id)
            if record is None:
                raise RoleOperationRejected(
                    "role_not_found", "No role with that id.", status_code=404
                )
            jd_id = record.job_description_document_id
            uow.roles.delete(workspace_id, role_id)
            uow.documents.hard_delete(workspace_id, jd_id)
            uow.commit()

    def reanalyse(self, workspace_id: str, role_id: str) -> tuple[RoleView, JobView]:
        cv = self.cv_store.get_active(workspace_id)
        if cv is None:
            raise RoleOperationRejected(
                "cv_required",
                "Upload a CV before reanalysing a role.",
                status_code=409,
            )
        with self._uow_factory() as uow:
            record = uow.roles.get(workspace_id, role_id)
            if record is None:
                raise RoleOperationRejected(
                    "role_not_found", "No role with that id.", status_code=404
                )
            jd = uow.documents.get(workspace_id, record.job_description_document_id)
            if jd is None:
                raise RoleOperationRejected(
                    "role_not_found",
                    "Job description for this role is missing.",
                    status_code=404,
                )
            description = jd.normalised_text

        bundle = analyse_hermetic(
            cv_text=cv.normalised_text,
            cv_document_id=cv.view.id,
            jd_text=description,
        )
        now = datetime.now(UTC)
        job_id = str(uuid.uuid4())
        queued = new_role_analysis_job(
            job_id=job_id,
            workspace_id=workspace_id,
            role_id=role_id,
            created_at=now,
        )
        terminal = mark_succeeded(
            mark_stage(mark_running(queued, at=now), JobStage.SCORING),
            at=now,
        )

        with self._uow_factory() as uow:
            bumped = uow.roles.bump_analysis_version(workspace_id, role_id)
            uow.documents.ensure_spans(workspace_id, cv.view.id, bundle.cv_claim_spans)
            # JD spans may be new ids from a fresh hermetic extract — persist them.
            uow.documents.ensure_spans(
                workspace_id, record.job_description_document_id, bundle.jd_spans
            )
            # Re-bind requirement source_span_ids onto the existing JD document id.
            requirements = tuple(
                Requirement(
                    id=req.id,
                    text=req.text,
                    competency=req.competency,
                    seniority_signal=req.seniority_signal,
                    must_have=req.must_have,
                    source_span_id=req.source_span_id,
                    extraction_confidence=req.extraction_confidence,
                    is_vague=req.is_vague,
                )
                for req in bundle.requirements
            )
            uow.jobs.enqueue(queued)
            uow.analysis.publish(
                workspace_id=workspace_id,
                role_id=role_id,
                analysis_version=bumped.analysis_version,
                cv_document_id=cv.view.id,
                requirements=requirements,
                claims=bundle.claims,
                mappings=bundle.mappings,
                explanation=bundle.explanation,
                job=terminal,
            )
            uow.commit()

        role = RoleView(
            id=role_id,
            title=record.title,
            company=record.company,
            fit_score=int(round(bundle.explanation.score)),
            band_label=band_label(bundle.explanation.band),
            counts=count_statuses(bundle.mappings),
            status="ready",
            updated_at=now,
            description=description,
        )
        job = JobView(
            id=job_id,
            kind=terminal.kind.value,
            state=terminal.state.value,
            stage=terminal.stage.value if terminal.stage else None,
            started_at=terminal.started_at,
            finished_at=terminal.finished_at,
            error=None,
        )
        return role, job

    def list_roles(self, workspace_id: str) -> tuple[RoleView, ...]:
        with self._uow_factory() as uow:
            records = uow.roles.list_for_workspace(workspace_id)
            return tuple(
                self._role_view(uow, workspace_id, record) for record in records
            )

    def get_role(self, workspace_id: str, role_id: str) -> RoleView | None:
        with self._uow_factory() as uow:
            record = uow.roles.get(workspace_id, role_id)
            if record is None:
                return None
            return self._role_view(uow, workspace_id, record)

    def get_job(self, workspace_id: str, job_id: str) -> JobView | None:
        with self._uow_factory() as uow:
            job = uow.jobs.get(workspace_id, job_id)
            if job is None:
                return None
            error = None
            if job.error is not None:
                error = f"{job.error.code}: {job.error.message}"
            return JobView(
                id=job.id,
                kind=job.kind.value,
                state=job.state.value,
                stage=job.stage.value if job.stage else None,
                started_at=job.started_at,
                finished_at=job.finished_at,
                error=error,
            )

    def require_analysis(self, workspace_id: str, role_id: str) -> AnalysisBundle:
        with self._uow_factory() as uow:
            record = uow.roles.get(workspace_id, role_id)
            if record is None:
                raise RoleOperationRejected(
                    "role_not_found", "No role with that id.", status_code=404
                )
            if record.status is not RoleStatus.READY:
                raise RoleOperationRejected(
                    "analysis_incomplete",
                    "Analysis has not finished for this role.",
                    status_code=409,
                )
            return self._load_bundle(uow, workspace_id, record)

    def save_cover_letter(self, workspace_id: str, role_id: str, draft: object) -> None:
        self._save_draft(
            workspace_id=workspace_id,
            role_id=role_id,
            draft=draft,
            kind="cover-letter",
            body=_cover_letter_body(draft),
            citation_span_ids=_paragraph_span_ids(draft),
        )

    def list_cover_letters(
        self, workspace_id: str, role_id: str
    ) -> tuple[GeneratedDraftRecord, ...]:
        return self._list_drafts(workspace_id, role_id, kind="cover-letter")

    def save_bullet_draft(self, workspace_id: str, role_id: str, draft: object) -> None:
        self._save_draft(
            workspace_id=workspace_id,
            role_id=role_id,
            draft=draft,
            kind="bullets",
            body=_bullet_body(draft),
            citation_span_ids=_bullet_span_ids(draft),
        )

    def list_bullet_drafts(
        self, workspace_id: str, role_id: str
    ) -> tuple[GeneratedDraftRecord, ...]:
        return self._list_drafts(workspace_id, role_id, kind="bullets")

    def _save_draft(
        self,
        *,
        workspace_id: str,
        role_id: str,
        draft: object,
        kind: str,
        body: str,
        citation_span_ids: tuple[str, ...],
    ) -> None:
        provider, model_tag, left_machine, _grounded, fallback = _provenance_bits(draft)
        with self._uow_factory() as uow:
            record = uow.roles.get(workspace_id, role_id)
            if record is None:
                raise RoleOperationRejected(
                    "role_not_found", "No role with that id.", status_code=404
                )
            uow.drafts.save(
                NewGeneratedDraft(
                    id=str(getattr(draft, "id")),
                    workspace_id=workspace_id,
                    role_id=role_id,
                    kind=kind,
                    body=body,
                    analysis_version=record.analysis_version,
                    citation_span_ids=citation_span_ids,
                    provider=provider,
                    model_tag=model_tag or "rules-v1",
                    left_machine=left_machine,
                    groundedness=GroundednessVerdict.PASS,
                    used_template_fallback=fallback == "template",
                    regeneration_count=0,
                )
            )
            uow.commit()

    def _list_drafts(
        self, workspace_id: str, role_id: str, *, kind: str
    ) -> tuple[GeneratedDraftRecord, ...]:
        with self._uow_factory() as uow:
            if uow.roles.get(workspace_id, role_id) is None:
                raise RoleOperationRejected(
                    "role_not_found", "No role with that id.", status_code=404
                )
            return uow.drafts.list_for_role(workspace_id, role_id, kind=kind)

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
            bundle = self.require_analysis(workspace_id, role.id)
            reqs = {r.id: r.text for r in bundle.requirements}
            because = tuple(
                reqs[m.requirement_id]
                for m in bundle.mappings
                if m.status is MappingStatus.MET and m.requirement_id in reqs
            )[:3]
            out.append((role, index, tied, because))
        return tuple(out)

    def _session(self, uow: SqlUnitOfWork) -> Session:
        session = uow._session  # noqa: SLF001
        assert session is not None
        return session

    def _role_view(
        self, uow: SqlUnitOfWork, workspace_id: str, record: RoleRecord
    ) -> RoleView:
        session = self._session(uow)
        score_row = session.scalar(
            select(ScoreExplanationRow).where(
                ScoreExplanationRow.workspace_id == uuid.UUID(workspace_id),
                ScoreExplanationRow.role_id == uuid.UUID(record.id),
                ScoreExplanationRow.analysis_version == record.analysis_version,
                ScoreExplanationRow.invalidated.is_(False),
            )
        )
        mappings = uow.analysis.list_mappings(workspace_id, record.id)
        fit_score = int(round(score_row.score)) if score_row is not None else 0
        band = score_row.band if score_row is not None else "limited"
        jd = uow.documents.get(workspace_id, record.job_description_document_id)
        description = jd.normalised_text if jd is not None else ""
        created = record.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        return RoleView(
            id=record.id,
            title=record.title,
            company=record.company,
            fit_score=fit_score,
            band_label=band_label(band),
            counts=count_statuses(mappings),
            status=record.status.value,
            updated_at=created,
            description=description,
        )

    def _load_bundle(
        self, uow: SqlUnitOfWork, workspace_id: str, record: RoleRecord
    ) -> AnalysisBundle:
        session = self._session(uow)
        wid = uuid.UUID(workspace_id)
        rid = uuid.UUID(record.id)
        req_rows = session.scalars(
            select(RequirementRow).where(
                RequirementRow.workspace_id == wid,
                RequirementRow.role_id == rid,
                RequirementRow.analysis_version == record.analysis_version,
            )
        ).all()
        requirements = tuple(
            Requirement(
                id=str(row.id),
                text=row.text,
                competency=row.competency,
                seniority_signal=None,
                must_have=row.must_have,
                source_span_id=str(row.source_span_id) if row.source_span_id else "",
                extraction_confidence=row.extraction_confidence or 0.0,
                is_vague=row.is_vague,
            )
            for row in req_rows
        )
        cv = uow.documents.get_active_cv(workspace_id)
        claims: tuple[Claim, ...] = ()
        if cv is not None:
            claim_rows = session.scalars(
                select(ClaimRow).where(
                    ClaimRow.workspace_id == wid,
                    ClaimRow.document_id == uuid.UUID(cv.id),
                )
            ).all()
            loaded: list[Claim] = []
            for row in claim_rows:
                span_ids = tuple(
                    str(link.span_id)
                    for link in session.scalars(
                        select(ClaimSpanRow).where(ClaimSpanRow.claim_id == row.id)
                    ).all()
                )
                loaded.append(
                    Claim(
                        id=str(row.id),
                        competency=row.competency,
                        context=row.context,
                        duration_signal=row.duration_signal or "",
                        recency_signal=row.recency_signal or "",
                        source_span_ids=span_ids,
                        extraction_confidence=0.85,
                    )
                )
            claims = tuple(loaded)
        mappings = uow.analysis.list_mappings(workspace_id, record.id)
        score_row = session.scalar(
            select(ScoreExplanationRow).where(
                ScoreExplanationRow.workspace_id == wid,
                ScoreExplanationRow.role_id == rid,
                ScoreExplanationRow.analysis_version == record.analysis_version,
                ScoreExplanationRow.invalidated.is_(False),
            )
        )
        if score_row is None:
            raise RoleOperationRejected(
                "analysis_incomplete",
                "Analysis has not finished for this role.",
                status_code=409,
            )
        payload = score_row.explanation
        components = tuple(
            ScoreComponent(
                requirement_id=str(c["requirement_id"]),
                must_have=bool(c["must_have"]),
                status=MappingStatus(str(c["status"])),
                weight=float(c["weight"]),
                status_factor=float(c["status_factor"]),
                recency_factor=float(c["recency_factor"]),
                contribution=float(c["contribution"]),
            )
            for c in payload.get("components", [])
        )
        explanation = ScoreExplanation(
            score=float(score_row.score),
            band=str(score_row.band),
            components=components,
            denominator=float(payload.get("denominator", 0.0)),
            numerator=float(payload.get("numerator", 0.0)),
        )
        return AnalysisBundle(
            requirements=requirements,
            claims=claims,
            mappings=mappings,
            explanation=explanation,
            jd_document_id=record.job_description_document_id,
            cv_document_id=cv.id if cv is not None else "",
        )


def _provenance_bits(
    draft: object,
) -> tuple[str, str | None, bool, bool, str]:
    prov = getattr(draft, "provenance", None)
    if prov is None:
        return "hermetic", "rules-v1", False, True, "template"
    return (
        str(getattr(prov, "provider", "hermetic")),
        getattr(prov, "model", None),
        bool(getattr(prov, "left_machine", False)),
        bool(getattr(prov, "grounded", True)),
        str(getattr(prov, "fallback", "template")),
    )


def _cover_letter_body(draft: object) -> str:
    return json.dumps(
        {
            "paragraphs": list(getattr(draft, "paragraphs", [])),
            "omitted_reason": getattr(draft, "omitted_reason", None),
            "generated_at": getattr(
                getattr(draft, "provenance", None), "generated_at", None
            ),
        }
    )


def _bullet_body(draft: object) -> str:
    return json.dumps(
        {
            "requirement_id": getattr(draft, "requirement_id", None),
            "bullets": list(getattr(draft, "bullets", [])),
            "generated_at": getattr(
                getattr(draft, "provenance", None), "generated_at", None
            ),
        }
    )


def _paragraph_span_ids(draft: object) -> tuple[str, ...]:
    ids: list[str] = []
    for paragraph in getattr(draft, "paragraphs", []):
        if not isinstance(paragraph, dict):
            continue
        raw = paragraph.get("spanIds", paragraph.get("span_ids", []))
        if isinstance(raw, list):
            ids.extend(str(item) for item in raw)
    return tuple(dict.fromkeys(ids))


def _bullet_span_ids(draft: object) -> tuple[str, ...]:
    ids: list[str] = []
    for bullet in getattr(draft, "bullets", []):
        if not isinstance(bullet, dict):
            continue
        raw = bullet.get("spanIds", bullet.get("span_ids", []))
        if isinstance(raw, list):
            ids.extend(str(item) for item in raw)
    return tuple(dict.fromkeys(ids))
