"""Record which matching pipeline a workspace chose and an analysis ran (PLAN 18.10).

Both columns default to v1, so every existing workspace and analysis keeps the
pipeline it already has.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a4d8e2f7c310"
down_revision = "e2c7a4b9d150"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"
TABLES = ("workspaces", "analysis_jobs")
ALLOWED = "pipeline_version IN ('v1', 'v2')"


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "pipeline_version",
                sa.String(length=8),
                nullable=False,
                server_default="v1",
            ),
            schema=APP_SCHEMA,
        )
        op.create_check_constraint(
            op.f(f"ck_{table}_pipeline_version"), table, ALLOWED, schema=APP_SCHEMA
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_constraint(
            op.f(f"ck_{table}_pipeline_version"),
            table,
            type_="check",
            schema=APP_SCHEMA,
        )
        op.drop_column(table, "pipeline_version", schema=APP_SCHEMA)
