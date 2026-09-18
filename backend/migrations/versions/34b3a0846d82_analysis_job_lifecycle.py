"""Add role status and full analysis job lifecycle columns."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "34b3a0846d82"
down_revision = "b7e2c1a90f44"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"


def upgrade() -> None:
    op.add_column(
        "roles",
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="analysing",
        ),
        schema=APP_SCHEMA,
    )
    op.alter_column(
        "analysis_jobs",
        "status",
        new_column_name="state",
        schema=APP_SCHEMA,
    )
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "kind",
            sa.String(length=32),
            nullable=False,
            server_default="role_analysis",
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("stage", sa.String(length=64), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("error_code", sa.String(length=64), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("error_message", sa.String(length=512), nullable=True),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_analysis_jobs_workspace_state",
        "analysis_jobs",
        ["workspace_id", "state"],
        unique=False,
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_analysis_jobs_workspace_state",
        table_name="analysis_jobs",
        schema=APP_SCHEMA,
    )
    op.drop_column("analysis_jobs", "error_message", schema=APP_SCHEMA)
    op.drop_column("analysis_jobs", "error_code", schema=APP_SCHEMA)
    op.drop_column("analysis_jobs", "finished_at", schema=APP_SCHEMA)
    op.drop_column("analysis_jobs", "started_at", schema=APP_SCHEMA)
    op.drop_column("analysis_jobs", "stage", schema=APP_SCHEMA)
    op.drop_column("analysis_jobs", "kind", schema=APP_SCHEMA)
    op.alter_column(
        "analysis_jobs",
        "state",
        new_column_name="status",
        schema=APP_SCHEMA,
    )
    op.drop_column("roles", "status", schema=APP_SCHEMA)
