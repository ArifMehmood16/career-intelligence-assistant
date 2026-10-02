"""SQLAlchemy models for the v2 pipeline (ADR 013, ADR 014, PLAN 18.3).

They share the application metadata and its Alembic history. Every row carries
workspace_id and cascades from what it was derived from: chunks and graph rows
from their document, embeddings, evidence and traces from their chunk, verdicts
from their analysis and requirement.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from career_assistant.adapters.persistence.models import Base

# Contact chunks are stored for citation resolution and never indexed.
FTS_EXPRESSION = (
    "CASE WHEN kind = 'contact' THEN NULL ELSE "
    "to_tsvector('english'::regconfig, coalesce(context, '') || ' ' || text) END"
)
_SCORE_RANGE = "BETWEEN 0 AND 4"


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _workspace() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )


def _owner(table: str, *, nullable: bool = False) -> Mapped[Any]:
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{table}.id", ondelete="CASCADE"),
        nullable=nullable,
    )


def _created_at() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ChunkRow(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "first_line", name="uq_chunks_document_line"),
        CheckConstraint("last_line >= first_line", name="line_range"),
        Index("ix_chunks_workspace_id", "workspace_id"),
        Index("ix_chunks_document_id", "document_id"),
        Index("ix_chunks_fts", "fts", postgresql_using="gin"),
        Index("ix_chunks_tech_terms", "tech_terms", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = _workspace()
    document_id: Mapped[uuid.UUID] = _owner("documents")
    first_line: Mapped[int] = mapped_column(Integer, nullable=False)
    last_line: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Model-written, for retrieval only; never shown or quoted as evidence.
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=sql_text("'{}'::jsonb")
    )
    tech_terms: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=sql_text("'{}'::text[]")
    )
    fts: Mapped[Any] = mapped_column(
        TSVECTOR, Computed(FTS_EXPRESSION, persisted=True), nullable=True
    )
    evidence_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    chunker_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    chunker_model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = _created_at()


class ChunkEmbeddingRow(Base):
    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "model_key", name="uq_chunk_embeddings_model"),
        Index("ix_chunk_embeddings_workspace_model", "workspace_id", "model_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = _workspace()
    chunk_id: Mapped[uuid.UUID] = _owner("chunks")
    # provider:model:dimensions:input_type — changing any of them re-embeds.
    model_key: Mapped[str] = mapped_column(String(256), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_tag: Mapped[str] = mapped_column(String(128), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    input_type: Mapped[str] = mapped_column(String(16), nullable=False)
    embedding: Mapped[Any] = mapped_column(Vector(), nullable=False)


class RequirementItemRow(Base):
    __tablename__ = "requirement_items"
    __table_args__ = (
        CheckConstraint("years_expected IS NULL OR years_expected >= 0", name="years"),
        Index("ix_requirement_items_workspace_id", "workspace_id"),
        Index("ix_requirement_items_role_id", "role_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = _workspace()
    role_id: Mapped[uuid.UUID] = _owner("roles")
    chunk_id: Mapped[uuid.UUID] = _owner("chunks")
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    must_have: Mapped[bool] = mapped_column(Boolean, nullable=False)
    years_expected: Mapped[float | None] = mapped_column(Float, nullable=True)
    seniority_expected: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tech_terms: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=sql_text("'{}'::text[]")
    )


class KgNodeRow(Base):
    __tablename__ = "kg_nodes"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "kind", "canonical_name", name="uq_kg_nodes_document_name"
        ),
        Index("ix_kg_nodes_workspace_name", "workspace_id", "canonical_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = _workspace()
    document_id: Mapped[uuid.UUID] = _owner("documents")
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sql_text("'{}'::jsonb")
    )


class KgEdgeRow(Base):
    __tablename__ = "kg_edges"
    __table_args__ = (
        # An asserted edge cites the chunk it came from; an inferred one cites
        # nothing, so it can never be shown as the candidate's evidence.
        CheckConstraint(
            "(provenance = 'asserted' AND chunk_id IS NOT NULL) OR "
            "(provenance = 'inferred' AND chunk_id IS NULL)",
            name="provenance_citation",
        ),
        Index("ix_kg_edges_workspace_id", "workspace_id"),
        Index("ix_kg_edges_source_id", "source_id"),
        Index("ix_kg_edges_target_id", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = _workspace()
    document_id: Mapped[uuid.UUID] = _owner("documents")
    source_id: Mapped[uuid.UUID] = _owner("kg_nodes")
    target_id: Mapped[uuid.UUID] = _owner("kg_nodes")
    relation: Mapped[str] = mapped_column(String(32), nullable=False)
    provenance: Mapped[str] = mapped_column(String(16), nullable=False)
    chunk_id: Mapped[uuid.UUID | None] = _owner("chunks", nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_tag: Mapped[str | None] = mapped_column(String(128), nullable=True)


class MatchVerdictRow(Base):
    __tablename__ = "match_verdicts"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "requirement_item_id", name="uq_match_verdicts_requirement"
        ),
        CheckConstraint(
            "verdict IN ('met', 'partial', 'missing')", name="verdict_value"
        ),
        CheckConstraint(f"match_score {_SCORE_RANGE}", name="match_score_range"),
        CheckConstraint(
            f"seniority_score IS NULL OR seniority_score {_SCORE_RANGE}",
            name="seniority_score_range",
        ),
        CheckConstraint(
            f"experience_score IS NULL OR experience_score {_SCORE_RANGE}",
            name="experience_score_range",
        ),
        Index("ix_match_verdicts_workspace_id", "workspace_id"),
        Index("ix_match_verdicts_input_hash", "input_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = _workspace()
    analysis_id: Mapped[uuid.UUID] = _owner("analysis_jobs")
    requirement_item_id: Mapped[uuid.UUID] = _owner("requirement_items")
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    match_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    seniority_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    experience_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # Recomputed at aggregation from the verdict; never cached with it.
    requirement_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # The validated judge JSON as returned, for audit and future fields.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_tag: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = _created_at()


class VerdictEvidenceRow(Base):
    __tablename__ = "verdict_evidence"
    __table_args__ = (
        Index("ix_verdict_evidence_workspace_id", "workspace_id"),
        Index("ix_verdict_evidence_verdict_id", "verdict_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = _workspace()
    verdict_id: Mapped[uuid.UUID] = _owner("match_verdicts")
    chunk_id: Mapped[uuid.UUID] = _owner("chunks")
    dimension: Mapped[str] = mapped_column(String(16), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)


class RetrievalTraceRow(Base):
    __tablename__ = "retrieval_traces"
    __table_args__ = (
        Index("ix_retrieval_traces_workspace_id", "workspace_id"),
        Index("ix_retrieval_traces_verdict_id", "verdict_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    workspace_id: Mapped[uuid.UUID] = _workspace()
    verdict_id: Mapped[uuid.UUID] = _owner("match_verdicts")
    round: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_id: Mapped[uuid.UUID] = _owner("chunks")
    dense_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lexical_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exact_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fused_score: Mapped[float] = mapped_column(Float, nullable=False)
