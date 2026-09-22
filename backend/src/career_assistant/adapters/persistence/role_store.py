"""SQL-backed role store — persist the JD and enqueue analysis; the worker publishes."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Protocol

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
from career_assistant.application.intake.errors import IntakeError
from career_assistant.application.observability.emit import emit_action
from career_assistant.application.ports.persistence import (
    GeneratedDraftRecord,
    NewDocument,
    NewGeneratedDraft,
    ParseStatus,
    RoleRecord,
)
from career_assistant.application.roles.hermetic_analysis import (
    AnalysisBundle,
    band_label,
    count_statuses,
)
from career_assistant.application.roles.store import (
    JobErrorView,
    JobView,
    RoleOperationRejected,
    RoleView,
)
from career_assistant.domain.attribution import AnalysisAttribution
from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import DocumentKind, Page, ParsedDocument, Span
from career_assistant.domain.groundedness import GroundednessVerdict
from career_assistant.domain.jobs import (
    AnalysisJob,
    RoleStatus,
    new_role_analysis_job,
)
from career_assistant.domain.mapping import MappingStatus
from career_assistant.domain.prompts import RetrievedSpan
from career_assistant.domain.ranking import RankableRole, rank_roles
from career_assistant.domain.requirements import ItemType, Requirement
from career_assistant.domain.scoring import ScoreComponent, ScoreExplanation
from career_assistant.logconfig import log_event
from career_assistant.parsing.pipeline import parse_pasted_text


class _ProvenanceLike(Protocol):
    provider: object
    model: object
    left_machine: object
    grounded: object
    fallback: object
    generated_at: object


class _DraftLike(Protocol):
    id: object
    provenance: _ProvenanceLike | None
    paragraphs: Sequence[object]
    bullets: Sequence[object]
    requirement_id: object
    omitted_reason: object


_log = logging.getLogger(__name__)


class SqlRoleStore:
    """RoleStore over SqlUnitOfWork. Create/reanalyse enqueue; the worker publishes."""

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

        try:
            parsed = parse_pasted_text(
                description,
                filename="job-description.txt",
                kind=DocumentKind.JOB_DESCRIPTION,
            )
        except IntakeError as exc:
            raise RoleOperationRejected(
                exc.code.value, exc.message, status_code=422
            ) from exc

        now = datetime.now(UTC)
        role_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        jd_document = _new_document_from_parsed(
            parsed, body=description.encode("utf-8")
        )
        queued = new_role_analysis_job(
            job_id=job_id,
            workspace_id=workspace_id,
            role_id=role_id,
            created_at=now,
        )

        with self._uow_factory() as uow:
            uow.workspaces.ensure(workspace_id)
            uow.documents.save_admitted(workspace_id, jd_document)
            uow.roles.create(
                workspace_id=workspace_id,
                role_id=role_id,
                title=title,
                company=company,
                job_description_document_id=parsed.document.id,
                status=RoleStatus.ANALYSING,
            )
            uow.jobs.enqueue(queued)
            uow.commit()
            record = uow.roles.get(workspace_id, role_id)
            assert record is not None
            log_event(
                _log,
                "sql.role.created",
                role_id=role_id,
                job_id=job_id,
                jd_document_id=parsed.document.id,
            )
            emit_action(
                "role.create",
                outcome="accepted",
                entity_type="role",
                entity_id=role_id,
                attributes={"id_role": role_id, "id_job": job_id},
            )
            return self._role_view(uow, workspace_id, record), _job_view(queued)

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
            log_event(_log, "sql.role.deleted", role_id=role_id)
            emit_action(
                "role.delete",
                outcome="succeeded",
                entity_type="role",
                entity_id=role_id,
            )

    def reanalyse(self, workspace_id: str, role_id: str) -> tuple[RoleView, JobView]:
        if self.cv_store.get_active(workspace_id) is None:
            raise RoleOperationRejected(
                "cv_required",
                "Upload a CV before reanalysing a role.",
                status_code=409,
            )
        now = datetime.now(UTC)
        with self._uow_factory() as uow:
            record = uow.roles.get(workspace_id, role_id)
            if record is None:
                raise RoleOperationRejected(
                    "role_not_found", "No role with that id.", status_code=404
                )
            active = uow.jobs.active_for_role(workspace_id, role_id)
            if active is not None:
                return self._role_view(uow, workspace_id, record), _job_view(active)
            uow.roles.bump_analysis_version(workspace_id, role_id)
            queued = new_role_analysis_job(
                job_id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                role_id=role_id,
                created_at=now,
            )
            uow.jobs.enqueue(queued)
            uow.commit()
            updated = uow.roles.get(workspace_id, role_id)
            assert updated is not None
            log_event(
                _log,
                "sql.role.reanalysed",
                role_id=role_id,
                job_id=queued.id,
            )
            emit_action(
                "role.reanalyse",
                outcome="accepted",
                entity_type="role",
                entity_id=role_id,
                attributes={"id_role": role_id, "id_job": queued.id},
            )
            return self._role_view(uow, workspace_id, updated), _job_view(queued)

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

    def get_span(
        self, workspace_id: str, span_id: str
    ) -> tuple[Span, tuple[Page, ...]] | None:
        with self._uow_factory() as uow:
            found = uow.documents.find_span(workspace_id, span_id)
            if found is None:
                return None
            span, _pages = found
            document = uow.documents.get(workspace_id, span.document_id)
            if document is None or document.kind is not DocumentKind.JOB_DESCRIPTION:
                return None
            return found

    def job_description_spans(self, workspace_id: str) -> tuple[RetrievedSpan, ...]:
        with self._uow_factory() as uow:
            items: list[RetrievedSpan] = []
            for record in uow.roles.list_for_workspace(workspace_id):
                items.extend(
                    RetrievedSpan(
                        span=span,
                        document_kind=DocumentKind.JOB_DESCRIPTION,
                        role_id=record.id,
                    )
                    for span in uow.documents.list_spans(
                        workspace_id, record.job_description_document_id
                    )
                )
            return tuple(items)

    def get_job(self, workspace_id: str, job_id: str) -> JobView | None:
        with self._uow_factory() as uow:
            job = uow.jobs.get(workspace_id, job_id)
            if job is None:
                return None
            return _job_view(job)

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

    def save_cover_letter(
        self, workspace_id: str, role_id: str, draft: _DraftLike
    ) -> None:
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

    def save_bullet_draft(
        self, workspace_id: str, role_id: str, draft: _DraftLike
    ) -> None:
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
        draft: _DraftLike,
        kind: str,
        body: str,
        citation_span_ids: tuple[str, ...],
    ) -> None:
        provider, model_tag, left_machine, grounded, fallback = _provenance_bits(draft)
        verdict = GroundednessVerdict.PASS if grounded else GroundednessVerdict.FAIL
        with self._uow_factory() as uow:
            record = uow.roles.get(workspace_id, role_id)
            if record is None:
                raise RoleOperationRejected(
                    "role_not_found", "No role with that id.", status_code=404
                )
            uow.drafts.save(
                NewGeneratedDraft(
                    id=str(draft.id),
                    workspace_id=workspace_id,
                    role_id=role_id,
                    kind=kind,
                    body=body,
                    analysis_version=record.analysis_version,
                    citation_span_ids=citation_span_ids,
                    provider=provider,
                    model_tag=model_tag or "rules-v1",
                    left_machine=left_machine,
                    groundedness=verdict,
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
        views = {
            role.id: role
            for role in self.list_roles(workspace_id)
            if role.status == RoleStatus.READY.value
        }
        candidates: list[RankableRole] = []
        for role in views.values():
            bundle = self.require_analysis(workspace_id, role.id)
            reqs = {item.id: item.text for item in bundle.requirements}
            because = tuple(
                reqs[mapping.requirement_id]
                for mapping in bundle.mappings
                if mapping.status is MappingStatus.MET
                and mapping.requirement_id in reqs
            )[:3]
            candidates.append(
                RankableRole(
                    id=role.id,
                    title=role.title,
                    fit_score=role.fit_score,
                    because=because,
                )
            )
        return tuple(
            (views[item.id], item.rank, item.tied, item.because)
            for item in rank_roles(candidates)
        )

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
        band = score_row.band if score_row is not None else "unscored"
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
                seniority_signal=row.seniority_signal,
                must_have=row.must_have,
                source_span_id=str(row.source_span_id) if row.source_span_id else "",
                extraction_confidence=row.extraction_confidence or 0.0,
                is_vague=row.is_vague,
                item_type=ItemType(row.item_type)
                if row.item_type
                else ItemType.REQUIREMENT,
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
                stored_technologies = row.technologies
                technologies = (
                    tuple(str(item) for item in stored_technologies)
                    if isinstance(stored_technologies, list)
                    else ()
                )
                confidence = row.extraction_confidence
                loaded.append(
                    Claim(
                        id=str(row.id),
                        competency=row.competency,
                        context=row.context,
                        duration_signal=row.duration_signal or "",
                        recency_signal=row.recency_signal or "",
                        source_span_ids=span_ids,
                        extraction_confidence=(
                            float(confidence) if confidence is not None else 0.0
                        ),
                        employer=row.employer or "",
                        title=row.title or "",
                        scope=row.scope or "",
                        technologies=technologies,
                        outcome=row.outcome or "",
                        period_start=row.period_start,
                        period_end=row.period_end,
                        self_authored=bool(row.self_authored),
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
                adjudicated=bool(c.get("adjudicated", False)),
            )
            for c in payload.get("components", [])
        )
        band = str(score_row.band)
        explanation = ScoreExplanation(
            score=float(score_row.score),
            band=band,
            components=components,
            denominator=float(payload.get("denominator", 0.0)),
            numerator=float(payload.get("numerator", 0.0)),
            publishable=band not in {"incomplete", "unscored"},
        )
        return AnalysisBundle(
            requirements=requirements,
            claims=claims,
            mappings=mappings,
            explanation=explanation,
            jd_document_id=record.job_description_document_id,
            cv_document_id=cv.id if cv is not None else "",
            attribution=AnalysisAttribution(
                provider=score_row.assessment_provider,
                model=score_row.assessment_model,
                prompt_version=score_row.prompt_version,
                rubric_version=score_row.rubric_version,
                left_machine=bool(score_row.left_machine),
                failure_status=score_row.failure_status or None,
            ),
        )


def _provenance_bits(
    draft: _DraftLike,
) -> tuple[str, str | None, bool, bool, str]:
    prov = draft.provenance
    if prov is None:
        return "hermetic", "rules-v1", False, True, "template"
    model = prov.model
    return (
        str(prov.provider),
        str(model) if model is not None else None,
        bool(prov.left_machine),
        bool(prov.grounded),
        str(prov.fallback),
    )


def _cover_letter_body(draft: _DraftLike) -> str:
    generated_at = None if draft.provenance is None else draft.provenance.generated_at
    return json.dumps(
        {
            "paragraphs": list(draft.paragraphs),
            "omitted_reason": draft.omitted_reason,
            "generated_at": generated_at,
        }
    )


def _bullet_body(draft: _DraftLike) -> str:
    generated_at = None if draft.provenance is None else draft.provenance.generated_at
    return json.dumps(
        {
            "requirement_id": draft.requirement_id,
            "bullets": list(draft.bullets),
            "generated_at": generated_at,
        }
    )


def _paragraph_span_ids(draft: _DraftLike) -> tuple[str, ...]:
    ids: list[str] = []
    for paragraph in draft.paragraphs:
        if not isinstance(paragraph, dict):
            continue
        raw = paragraph.get("spanIds", paragraph.get("span_ids", []))
        if isinstance(raw, list):
            ids.extend(str(item) for item in raw)
    return tuple(dict.fromkeys(ids))


def _bullet_span_ids(draft: _DraftLike) -> tuple[str, ...]:
    ids: list[str] = []
    for bullet in draft.bullets:
        if not isinstance(bullet, dict):
            continue
        raw = bullet.get("spanIds", bullet.get("span_ids", []))
        if isinstance(raw, list):
            ids.extend(str(item) for item in raw)
    return tuple(dict.fromkeys(ids))


def _job_view(job: AnalysisJob) -> JobView:
    error = None
    if job.error is not None:
        error = JobErrorView(code=job.error.code, message=job.error.message)
    return JobView(
        id=job.id,
        kind=job.kind.value,
        state=job.state.value,
        stage=job.stage.value if job.stage else None,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error=error,
    )


def _new_document_from_parsed(parsed: ParsedDocument, *, body: bytes) -> NewDocument:
    return NewDocument(
        id=parsed.document.id,
        kind=DocumentKind.JOB_DESCRIPTION,
        filename=parsed.document.filename,
        media_type="text/plain",
        original_bytes=body,
        sha256=hashlib.sha256(body).hexdigest(),
        normalised_text="\n\n".join(page.text for page in parsed.pages),
        parse_status=ParseStatus.PARSED,
        page_count=parsed.document.page_count,
        character_count=parsed.document.character_count,
        is_active=False,
        spans=parsed.spans,
    )
