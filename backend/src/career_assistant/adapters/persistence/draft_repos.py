"""SQLAlchemy repository for generated draft artefacts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from career_assistant.adapters.persistence.models import (
    DraftCitationRow,
    GeneratedDraftRow,
)
from career_assistant.application.ports.persistence import (
    GeneratedDraftRecord,
    NewGeneratedDraft,
)
from career_assistant.domain.groundedness import GroundednessVerdict


def _as_uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def _to_record(
    row: GeneratedDraftRow, citation_span_ids: tuple[str, ...]
) -> GeneratedDraftRecord:
    return GeneratedDraftRecord(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        role_id=str(row.role_id),
        kind=row.kind,
        body=row.body,
        analysis_version=row.analysis_version,
        version=row.version,
        citation_span_ids=citation_span_ids,
        provider=row.provider,
        model_tag=row.model_tag,
        left_machine=row.left_machine,
        groundedness=GroundednessVerdict(row.groundedness),
        used_template_fallback=row.used_template_fallback,
        regeneration_count=row.regeneration_count,
        created_at=row.created_at or datetime.now(UTC),
    )


class SqlDraftRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, draft: NewGeneratedDraft) -> GeneratedDraftRecord:
        if (
            draft.groundedness is not GroundednessVerdict.PASS
            and not draft.used_template_fallback
        ):
            raise ValueError(
                "ungrounded drafts cannot be persisted (groundedness must be "
                "pass unless template fallback was used)"
            )
        next_version = self._next_version(draft.workspace_id, draft.role_id, draft.kind)
        row = GeneratedDraftRow(
            id=_as_uuid(draft.id),
            workspace_id=_as_uuid(draft.workspace_id),
            role_id=_as_uuid(draft.role_id),
            kind=draft.kind,
            body=draft.body,
            provider=draft.provider,
            model_tag=draft.model_tag,
            left_machine=draft.left_machine,
            analysis_version=draft.analysis_version,
            version=next_version,
            groundedness=draft.groundedness.value,
            used_template_fallback=draft.used_template_fallback,
            regeneration_count=draft.regeneration_count,
            invalidated=False,
        )
        self._session.add(row)
        self._session.flush()
        for span_id in draft.citation_span_ids:
            self._session.add(
                DraftCitationRow(
                    workspace_id=_as_uuid(draft.workspace_id),
                    draft_id=row.id,
                    span_id=_as_uuid(span_id),
                )
            )
        self._session.flush()
        return _to_record(row, draft.citation_span_ids)

    def get(self, workspace_id: str, draft_id: str) -> GeneratedDraftRecord | None:
        row = self._session.scalar(
            select(GeneratedDraftRow).where(
                GeneratedDraftRow.workspace_id == _as_uuid(workspace_id),
                GeneratedDraftRow.id == _as_uuid(draft_id),
            )
        )
        if row is None:
            return None
        return _to_record(row, self._citations(row.id))

    def list_for_role(
        self, workspace_id: str, role_id: str, *, kind: str | None = None
    ) -> tuple[GeneratedDraftRecord, ...]:
        stmt = (
            select(GeneratedDraftRow)
            .where(
                GeneratedDraftRow.workspace_id == _as_uuid(workspace_id),
                GeneratedDraftRow.role_id == _as_uuid(role_id),
            )
            .order_by(GeneratedDraftRow.version.asc())
        )
        if kind is not None:
            stmt = stmt.where(GeneratedDraftRow.kind == kind)
        rows = self._session.scalars(stmt).all()
        return tuple(_to_record(row, self._citations(row.id)) for row in rows)

    def get_latest(
        self, workspace_id: str, role_id: str, *, kind: str
    ) -> GeneratedDraftRecord | None:
        row = self._session.scalar(
            select(GeneratedDraftRow)
            .where(
                GeneratedDraftRow.workspace_id == _as_uuid(workspace_id),
                GeneratedDraftRow.role_id == _as_uuid(role_id),
                GeneratedDraftRow.kind == kind,
            )
            .order_by(GeneratedDraftRow.version.desc())
            .limit(1)
        )
        if row is None:
            return None
        return _to_record(row, self._citations(row.id))

    def _next_version(self, workspace_id: str, role_id: str, kind: str) -> int:
        current = self._session.scalar(
            select(func.max(GeneratedDraftRow.version)).where(
                GeneratedDraftRow.workspace_id == _as_uuid(workspace_id),
                GeneratedDraftRow.role_id == _as_uuid(role_id),
                GeneratedDraftRow.kind == kind,
            )
        )
        return int(current or 0) + 1

    def _citations(self, draft_id: uuid.UUID) -> tuple[str, ...]:
        rows = self._session.scalars(
            select(DraftCitationRow).where(DraftCitationRow.draft_id == draft_id)
        ).all()
        return tuple(str(row.span_id) for row in rows)
