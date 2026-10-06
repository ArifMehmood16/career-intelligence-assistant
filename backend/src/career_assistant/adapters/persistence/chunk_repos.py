"""SQL chunk and chunk-vector repository (ADR 013, PLAN 18.10).

Everything a validated chunk carries beyond its text and bounds — skills, verified
terms, the role, the role reference and advert requirements — lives in the
metadata column, so a stored chunk reloads equal to the one the chunker accepted.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from career_assistant.adapters.persistence.models import SpanRow
from career_assistant.adapters.persistence.models_v2 import ChunkEmbeddingRow, ChunkRow
from career_assistant.application.ports.chunks import (
    ChunkProvenance,
    ChunkVector,
    EmbeddingModel,
    StoredChunk,
)
from career_assistant.application.roles.analysis import chunk_span
from career_assistant.domain.chunking import (
    AtomicRequirementProposal,
    Chunk,
    RoleProposal,
    TechTermProposal,
)
from career_assistant.domain.recency import DateRange


class SqlChunkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_chunks(
        self, workspace_id: str, document_id: str, *, prompt_version: str
    ) -> tuple[StoredChunk, ...]:
        rows = self._session.scalars(
            select(ChunkRow)
            .where(
                ChunkRow.workspace_id == uuid.UUID(workspace_id),
                ChunkRow.document_id == uuid.UUID(document_id),
                ChunkRow.prompt_version == prompt_version,
            )
            .order_by(ChunkRow.first_line)
        ).all()
        return tuple(_stored(row) for row in rows)

    def replace_chunks(
        self,
        workspace_id: str,
        document_id: str,
        chunks: Sequence[Chunk],
        provenance: ChunkProvenance,
    ) -> tuple[StoredChunk, ...]:
        ws, doc = uuid.UUID(workspace_id), uuid.UUID(document_id)
        self._session.execute(
            delete(ChunkRow).where(
                ChunkRow.workspace_id == ws, ChunkRow.document_id == doc
            )
        )
        rows = [_row(ws, doc, chunk, provenance) for chunk in chunks]
        self._session.add_all(rows)
        self._session.flush()
        stored = tuple(_stored(row) for row in rows)
        for item in stored:
            span = chunk_span(item)
            if self._session.get(SpanRow, uuid.UUID(span.id)) is None:
                self._session.add(
                    SpanRow(
                        id=uuid.UUID(span.id),
                        workspace_id=ws,
                        document_id=doc,
                        page_number=span.page_number,
                        start_offset=span.start_offset,
                        end_offset=span.end_offset,
                        text=span.text,
                    )
                )
        self._session.flush()
        return stored

    def load_chunks(
        self, workspace_id: str, chunk_ids: Sequence[str]
    ) -> tuple[StoredChunk, ...]:
        wanted = [uuid.UUID(chunk_id) for chunk_id in chunk_ids]
        rows = self._session.scalars(
            select(ChunkRow).where(
                ChunkRow.workspace_id == uuid.UUID(workspace_id),
                ChunkRow.id.in_(wanted),
            )
        ).all()
        by_id = {row.id: row for row in rows}
        return tuple(_stored(by_id[cid]) for cid in wanted if cid in by_id)

    def embedded_chunk_ids(
        self, workspace_id: str, document_id: str, model_key: str
    ) -> frozenset[str]:
        ids = self._session.scalars(
            select(ChunkEmbeddingRow.chunk_id)
            .join(ChunkRow, ChunkRow.id == ChunkEmbeddingRow.chunk_id)
            .where(
                ChunkEmbeddingRow.workspace_id == uuid.UUID(workspace_id),
                ChunkEmbeddingRow.model_key == model_key,
                ChunkRow.document_id == uuid.UUID(document_id),
            )
        )
        return frozenset(str(chunk_id) for chunk_id in ids)

    def save_vectors(
        self, workspace_id: str, model: EmbeddingModel, vectors: Sequence[ChunkVector]
    ) -> None:
        ws = uuid.UUID(workspace_id)
        self._session.add_all(
            ChunkEmbeddingRow(
                workspace_id=ws,
                chunk_id=uuid.UUID(item.chunk_id),
                model_key=model.key,
                provider=model.provider_id,
                model_tag=model.model_tag,
                dimensions=model.dimensions,
                input_type=model.input_type,
                embedding=list(item.vector),
            )
            for item in vectors
        )
        self._session.flush()


def _row(
    ws: uuid.UUID, doc: uuid.UUID, chunk: Chunk, provenance: ChunkProvenance
) -> ChunkRow:
    return ChunkRow(
        id=uuid.uuid4(),
        workspace_id=ws,
        document_id=doc,
        first_line=chunk.first_line,
        last_line=chunk.last_line,
        start_offset=chunk.start_offset,
        end_offset=chunk.end_offset,
        kind=chunk.kind,
        text=chunk.text,
        context=chunk.context,
        metadata_=_metadata(chunk),
        tech_terms=sorted({t.surface.casefold() for t in chunk.tech_terms}),
        evidence_eligible=chunk.evidence_eligible,
        chunker_provider=provenance.provider_id,
        chunker_model=provenance.model_tag,
        prompt_version=provenance.prompt_version,
    )


def _stored(row: ChunkRow) -> StoredChunk:
    meta = row.metadata_
    chunk = Chunk(
        first_line=row.first_line,
        last_line=row.last_line,
        start_offset=row.start_offset,
        end_offset=row.end_offset,
        kind=row.kind,
        text=row.text,
        evidence_eligible=row.evidence_eligible,
        context=row.context,
        skills=tuple(meta.get("skills", ())),
        tech_terms=_terms(meta.get("tech_terms", ())),
        role=_role(meta.get("role")),
        role_ref=meta.get("role_ref"),
        atomic_requirements=tuple(
            _requirement(item) for item in meta.get("atomic_requirements", ())
        ),
    )
    return StoredChunk(
        chunk_id=str(row.id), document_id=str(row.document_id), chunk=chunk
    )


def _metadata(chunk: Chunk) -> dict[str, Any]:
    return {
        "skills": list(chunk.skills),
        "tech_terms": _terms_json(chunk.tech_terms),
        "role": _role_json(chunk.role),
        "role_ref": chunk.role_ref,
        "atomic_requirements": [
            {
                "quote": item.quote,
                "statement": item.statement,
                "must_have": item.must_have,
                "years_expected": item.years_expected,
                "experience_expected": item.experience_expected,
                "seniority_expected": item.seniority_expected,
                "tech_terms": _terms_json(item.tech_terms),
            }
            for item in chunk.atomic_requirements
        ],
    }


def _terms_json(terms: Sequence[TechTermProposal]) -> list[dict[str, str]]:
    return [{"surface": t.surface, "canonical": t.canonical} for t in terms]


def _terms(items: Sequence[Mapping[str, str]]) -> tuple[TechTermProposal, ...]:
    return tuple(
        TechTermProposal(surface=item["surface"], canonical=item["canonical"])
        for item in items
    )


def _role_json(role: RoleProposal | None) -> dict[str, Any] | None:
    if role is None:
        return None
    return {
        "employer": role.employer,
        "title": role.title,
        "date_text": role.date_text,
        "seniority_level": role.seniority_level,
        "dates": _dates_json(role.dates),
    }


def _role(item: Mapping[str, Any] | None) -> RoleProposal | None:
    if item is None:
        return None
    return RoleProposal(
        employer=item["employer"],
        title=item["title"],
        date_text=item["date_text"],
        seniority_level=item["seniority_level"],
        dates=_dates(item["dates"]),
    )


def _dates_json(dates: DateRange | None) -> dict[str, str | None] | None:
    if dates is None:
        return None
    end = dates.end.isoformat() if dates.end is not None else None
    return {"start": dates.start.isoformat(), "end": end}


def _dates(item: Mapping[str, str | None] | None) -> DateRange | None:
    if item is None or item["start"] is None:
        return None
    end = item["end"]
    return DateRange(
        start=date.fromisoformat(item["start"]),
        end=date.fromisoformat(end) if end is not None else None,
    )


def _requirement(item: Mapping[str, Any]) -> AtomicRequirementProposal:
    return AtomicRequirementProposal(
        quote=item["quote"],
        statement=item["statement"],
        must_have=item["must_have"],
        years_expected=item["years_expected"],
        seniority_expected=item["seniority_expected"],
        experience_expected=item.get("experience_expected"),
        tech_terms=_terms(item["tech_terms"]),
    )
