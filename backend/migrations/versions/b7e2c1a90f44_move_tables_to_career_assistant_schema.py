"""Move application tables from public into the career_assistant schema."""

from __future__ import annotations

from alembic import op

revision = "b7e2c1a90f44"
down_revision = "4569bacdd3ce"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"

# Dependency-safe order is not required for SET SCHEMA; Postgres rewrites FKs.
_TABLES = (
    "mapping_spans",
    "mappings",
    "draft_citations",
    "answer_citations",
    "score_explanations",
    "requirements",
    "generated_drafts",
    "embeddings",
    "claim_spans",
    "answers",
    "analysis_jobs",
    "spans",
    "roles",
    "questions",
    "claims",
    "chunks",
    "provider_settings",
    "provider_call_accounting",
    "documents",
    "conversations",
    "workspaces",
)


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {APP_SCHEMA}")
    for table in _TABLES:
        op.execute(
            f"ALTER TABLE IF EXISTS public.{table} SET SCHEMA {APP_SCHEMA}"
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(
            f"ALTER TABLE IF EXISTS {APP_SCHEMA}.{table} SET SCHEMA public"
        )
    op.execute(f"DROP SCHEMA IF EXISTS {APP_SCHEMA}")
