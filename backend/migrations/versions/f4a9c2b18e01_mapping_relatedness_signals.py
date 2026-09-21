"""Persist relatedness signals on requirement mappings."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f4a9c2b18e01"
down_revision = "e9b7c4d1a2f0"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"


def upgrade() -> None:
    op.add_column(
        "mappings",
        sa.Column("signals", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("mappings", "signals", schema=APP_SCHEMA)
