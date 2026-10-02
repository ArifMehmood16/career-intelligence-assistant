"""Persist planned and attempted provider calls in analysis progress."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b2d9c8e4f601"
down_revision = "c1f7a2d94e08"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"
TABLE = "analysis_job_tasks"


def upgrade() -> None:
    for operation in ("model", "embedding"):
        op.add_column(
            TABLE,
            sa.Column(
                f"{operation}_calls_done",
                sa.Integer(),
                server_default="0",
                nullable=False,
            ),
            schema=APP_SCHEMA,
        )
        op.add_column(
            TABLE,
            sa.Column(f"{operation}_calls_total", sa.Integer(), nullable=True),
            schema=APP_SCHEMA,
        )
        op.create_check_constraint(
            op.f(f"ck_{TABLE}_{operation}_calls"),
            TABLE,
            f"{operation}_calls_done >= 0 AND ({operation}_calls_total IS NULL OR "
            f"{operation}_calls_done <= {operation}_calls_total)",
            schema=APP_SCHEMA,
        )


def downgrade() -> None:
    for operation in ("embedding", "model"):
        op.drop_constraint(
            op.f(f"ck_{TABLE}_{operation}_calls"), TABLE, schema=APP_SCHEMA
        )
        op.drop_column(TABLE, f"{operation}_calls_total", schema=APP_SCHEMA)
        op.drop_column(TABLE, f"{operation}_calls_done", schema=APP_SCHEMA)
