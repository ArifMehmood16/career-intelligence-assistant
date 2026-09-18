"""Add company column to roles for the API Role contract."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "71f0c6b9147f"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"


def upgrade() -> None:
    op.add_column(
        "roles",
        sa.Column(
            "company",
            sa.String(length=512),
            nullable=False,
            server_default="",
        ),
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("roles", "company", schema=APP_SCHEMA)
