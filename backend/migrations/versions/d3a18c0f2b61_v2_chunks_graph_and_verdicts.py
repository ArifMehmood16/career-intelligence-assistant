"""v2 schema: chunks, chunk vectors, requirement items, the knowledge graph and verdicts.

PLAN 18.3, ADR 013 and ADR 014. pgvector moves into the `extensions` schema, where
Supabase keeps extensions, and row-level security is enabled with no policies on
every application table, so a role that is not the owner reads nothing even if
the schema is ever exposed through a data API.
"""

from __future__ import annotations

import pgvector.sqlalchemy.vector
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d3a18c0f2b61"
down_revision = "c9d2e4f61a08"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"
EXTENSIONS_SCHEMA = "extensions"
V2_TABLES = (
    "chunks",
    "chunk_embeddings",
    "requirement_items",
    "kg_nodes",
    "kg_edges",
    "match_verdicts",
    "verdict_evidence",
    "retrieval_traces",
)


def _move_vector(schema: str) -> str:
    """Move pgvector into `schema` when it is installed somewhere else."""
    return f"""
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace
    WHERE e.extname = 'vector' AND n.nspname <> '{schema}'
  ) THEN
    ALTER EXTENSION vector SET SCHEMA {schema};
  END IF;
END $$;
"""


def _set_row_level_security(enabled: bool) -> None:
    action = "ENABLE" if enabled else "DISABLE"
    op.execute(
        f"""
DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = '{APP_SCHEMA}' LOOP
    EXECUTE format('ALTER TABLE {APP_SCHEMA}.%I {action} ROW LEVEL SECURITY', t.tablename);
  END LOOP;
END $$;
"""
    )


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {EXTENSIONS_SCHEMA}")
    op.execute(_move_vector(EXTENSIONS_SCHEMA))
    op.execute(f"CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA {EXTENSIONS_SCHEMA}")
    # The vector type resolves through the search path when the tables are created.
    op.execute(f"SET LOCAL search_path TO {APP_SCHEMA}, {EXTENSIONS_SCHEMA}, public")
    op.create_table(
        "chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("first_line", sa.Integer(), nullable=False),
        sa.Column("last_line", sa.Integer(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "tech_terms",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "fts",
            postgresql.TSVECTOR(),
            sa.Computed(
                "CASE WHEN kind = 'contact' THEN NULL ELSE to_tsvector('english'::regconfig, coalesce(context, '') || ' ' || text) END",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column("evidence_eligible", sa.Boolean(), nullable=False),
        sa.Column("chunker_provider", sa.String(length=64), nullable=False),
        sa.Column("chunker_model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "last_line >= first_line", name=op.f("ck_chunks_line_range")
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["career_assistant.documents.id"],
            name=op.f("fk_chunks_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["career_assistant.workspaces.id"],
            name=op.f("fk_chunks_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chunks")),
        sa.UniqueConstraint(
            "document_id", "first_line", name="uq_chunks_document_line"
        ),
        schema="career_assistant",
    )
    op.create_index(
        "ix_chunks_document_id",
        "chunks",
        ["document_id"],
        unique=False,
        schema="career_assistant",
    )
    op.create_index(
        "ix_chunks_fts",
        "chunks",
        ["fts"],
        unique=False,
        schema="career_assistant",
        postgresql_using="gin",
    )
    op.create_index(
        "ix_chunks_tech_terms",
        "chunks",
        ["tech_terms"],
        unique=False,
        schema="career_assistant",
        postgresql_using="gin",
    )
    op.create_index(
        "ix_chunks_workspace_id",
        "chunks",
        ["workspace_id"],
        unique=False,
        schema="career_assistant",
    )
    op.create_table(
        "chunk_embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("model_key", sa.String(length=256), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_tag", sa.String(length=128), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("input_type", sa.String(length=16), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(), nullable=False),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["career_assistant.chunks.id"],
            name=op.f("fk_chunk_embeddings_chunk_id_chunks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["career_assistant.workspaces.id"],
            name=op.f("fk_chunk_embeddings_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chunk_embeddings")),
        sa.UniqueConstraint("chunk_id", "model_key", name="uq_chunk_embeddings_model"),
        schema="career_assistant",
    )
    op.create_index(
        "ix_chunk_embeddings_workspace_model",
        "chunk_embeddings",
        ["workspace_id", "model_key"],
        unique=False,
        schema="career_assistant",
    )
    op.create_table(
        "requirement_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("must_have", sa.Boolean(), nullable=False),
        sa.Column("years_expected", sa.Float(), nullable=True),
        sa.Column("seniority_expected", sa.String(length=16), nullable=True),
        sa.Column(
            "tech_terms",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "years_expected IS NULL OR years_expected >= 0",
            name=op.f("ck_requirement_items_years"),
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["career_assistant.chunks.id"],
            name=op.f("fk_requirement_items_chunk_id_chunks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["career_assistant.roles.id"],
            name=op.f("fk_requirement_items_role_id_roles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["career_assistant.workspaces.id"],
            name=op.f("fk_requirement_items_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_requirement_items")),
        schema="career_assistant",
    )
    op.create_index(
        "ix_requirement_items_role_id",
        "requirement_items",
        ["role_id"],
        unique=False,
        schema="career_assistant",
    )
    op.create_index(
        "ix_requirement_items_workspace_id",
        "requirement_items",
        ["workspace_id"],
        unique=False,
        schema="career_assistant",
    )
    op.create_table(
        "kg_nodes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column(
            "properties",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["career_assistant.documents.id"],
            name=op.f("fk_kg_nodes_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["career_assistant.workspaces.id"],
            name=op.f("fk_kg_nodes_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kg_nodes")),
        sa.UniqueConstraint(
            "document_id", "kind", "canonical_name", name="uq_kg_nodes_document_name"
        ),
        schema="career_assistant",
    )
    op.create_index(
        "ix_kg_nodes_workspace_name",
        "kg_nodes",
        ["workspace_id", "canonical_name"],
        unique=False,
        schema="career_assistant",
    )
    op.create_table(
        "kg_edges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("relation", sa.String(length=32), nullable=False),
        sa.Column("provenance", sa.String(length=16), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model_tag", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "(provenance = 'asserted' AND chunk_id IS NOT NULL) OR (provenance = 'inferred' AND chunk_id IS NULL)",
            name=op.f("ck_kg_edges_provenance_citation"),
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["career_assistant.chunks.id"],
            name=op.f("fk_kg_edges_chunk_id_chunks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["career_assistant.documents.id"],
            name=op.f("fk_kg_edges_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["career_assistant.kg_nodes.id"],
            name=op.f("fk_kg_edges_source_id_kg_nodes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["career_assistant.kg_nodes.id"],
            name=op.f("fk_kg_edges_target_id_kg_nodes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["career_assistant.workspaces.id"],
            name=op.f("fk_kg_edges_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kg_edges")),
        schema="career_assistant",
    )
    op.create_index(
        "ix_kg_edges_source_id",
        "kg_edges",
        ["source_id"],
        unique=False,
        schema="career_assistant",
    )
    op.create_index(
        "ix_kg_edges_target_id",
        "kg_edges",
        ["target_id"],
        unique=False,
        schema="career_assistant",
    )
    op.create_index(
        "ix_kg_edges_workspace_id",
        "kg_edges",
        ["workspace_id"],
        unique=False,
        schema="career_assistant",
    )
    op.create_table(
        "match_verdicts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("requirement_item_id", sa.UUID(), nullable=False),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("match_score", sa.SmallInteger(), nullable=False),
        sa.Column("seniority_score", sa.SmallInteger(), nullable=True),
        sa.Column("experience_score", sa.SmallInteger(), nullable=True),
        sa.Column("requirement_score", sa.Float(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_tag", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("contract_version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "verdict IN ('met', 'partial', 'missing')",
            name=op.f("ck_match_verdicts_verdict_value"),
        ),
        sa.CheckConstraint(
            "experience_score IS NULL OR experience_score BETWEEN 0 AND 4",
            name=op.f("ck_match_verdicts_experience_score_range"),
        ),
        sa.CheckConstraint(
            "match_score BETWEEN 0 AND 4",
            name=op.f("ck_match_verdicts_match_score_range"),
        ),
        sa.CheckConstraint(
            "seniority_score IS NULL OR seniority_score BETWEEN 0 AND 4",
            name=op.f("ck_match_verdicts_seniority_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["career_assistant.analysis_jobs.id"],
            name=op.f("fk_match_verdicts_analysis_id_analysis_jobs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_item_id"],
            ["career_assistant.requirement_items.id"],
            name=op.f("fk_match_verdicts_requirement_item_id_requirement_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["career_assistant.workspaces.id"],
            name=op.f("fk_match_verdicts_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_verdicts")),
        sa.UniqueConstraint(
            "analysis_id", "requirement_item_id", name="uq_match_verdicts_requirement"
        ),
        schema="career_assistant",
    )
    op.create_index(
        "ix_match_verdicts_input_hash",
        "match_verdicts",
        ["input_hash"],
        unique=False,
        schema="career_assistant",
    )
    op.create_index(
        "ix_match_verdicts_workspace_id",
        "match_verdicts",
        ["workspace_id"],
        unique=False,
        schema="career_assistant",
    )
    op.create_table(
        "verdict_evidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("verdict_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("dimension", sa.String(length=16), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["career_assistant.chunks.id"],
            name=op.f("fk_verdict_evidence_chunk_id_chunks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["verdict_id"],
            ["career_assistant.match_verdicts.id"],
            name=op.f("fk_verdict_evidence_verdict_id_match_verdicts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["career_assistant.workspaces.id"],
            name=op.f("fk_verdict_evidence_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verdict_evidence")),
        schema="career_assistant",
    )
    op.create_index(
        "ix_verdict_evidence_verdict_id",
        "verdict_evidence",
        ["verdict_id"],
        unique=False,
        schema="career_assistant",
    )
    op.create_index(
        "ix_verdict_evidence_workspace_id",
        "verdict_evidence",
        ["workspace_id"],
        unique=False,
        schema="career_assistant",
    )
    op.create_table(
        "retrieval_traces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("verdict_id", sa.UUID(), nullable=False),
        sa.Column("round", sa.SmallInteger(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("dense_rank", sa.Integer(), nullable=True),
        sa.Column("lexical_rank", sa.Integer(), nullable=True),
        sa.Column("exact_rank", sa.Integer(), nullable=True),
        sa.Column("fused_score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["career_assistant.chunks.id"],
            name=op.f("fk_retrieval_traces_chunk_id_chunks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["verdict_id"],
            ["career_assistant.match_verdicts.id"],
            name=op.f("fk_retrieval_traces_verdict_id_match_verdicts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["career_assistant.workspaces.id"],
            name=op.f("fk_retrieval_traces_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retrieval_traces")),
        schema="career_assistant",
    )
    op.create_index(
        "ix_retrieval_traces_verdict_id",
        "retrieval_traces",
        ["verdict_id"],
        unique=False,
        schema="career_assistant",
    )
    op.create_index(
        "ix_retrieval_traces_workspace_id",
        "retrieval_traces",
        ["workspace_id"],
        unique=False,
        schema="career_assistant",
    )
    _set_row_level_security(True)


def downgrade() -> None:
    _set_row_level_security(False)
    for table in reversed(V2_TABLES):
        op.drop_table(table, schema=APP_SCHEMA)
    # Older revisions resolve the vector type through the default search path, so
    # pgvector goes back to public. On Supabase, which keeps extensions in their own
    # schema, a downgrade below this revision is not a supported path.
    op.execute(_move_vector("public"))
