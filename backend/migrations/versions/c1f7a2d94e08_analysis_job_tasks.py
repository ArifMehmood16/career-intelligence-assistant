"""Store each analysis job's task progress: counts and timestamps only.

The worker writes a row per task as it moves; the API reads them back for
progress and the time-left estimate. Rows go with their job, and so with the
role or workspace. Row-level security is on with no policies, like every other
table in the schema (ADR 013).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c1f7a2d94e08"
down_revision = "a4d8e2f7c310"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"
TABLE = "analysis_job_tasks"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("units_done", sa.Integer(), server_default="0", nullable=False),
        sa.Column("units_total", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('pending', 'running', 'done', 'skipped')",
            name=op.f(f"ck_{TABLE}_state"),
        ),
        sa.CheckConstraint(
            "units_done >= 0 AND (units_total IS NULL OR units_done <= units_total)",
            name=op.f(f"ck_{TABLE}_units"),
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            [f"{APP_SCHEMA}.analysis_jobs.id"],
            name=op.f(f"fk_{TABLE}_job_id_analysis_jobs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            [f"{APP_SCHEMA}.workspaces.id"],
            name=op.f(f"fk_{TABLE}_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("job_id", "key", name=op.f(f"pk_{TABLE}")),
        schema=APP_SCHEMA,
    )
    op.create_index(
        op.f(f"ix_{TABLE}_workspace_id"),
        TABLE,
        ["workspace_id"],
        schema=APP_SCHEMA,
    )
    op.execute(f"ALTER TABLE {APP_SCHEMA}.{TABLE} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index(op.f(f"ix_{TABLE}_workspace_id"), TABLE, schema=APP_SCHEMA)
    op.drop_table(TABLE, schema=APP_SCHEMA)
