"""Persist item types, self-authored claims, and adjudication flags."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f5b0d3c29f12"
down_revision = "f4a9c2b18e01"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"


def upgrade() -> None:
    op.add_column(
        "requirements",
        sa.Column(
            "item_type",
            sa.String(length=32),
            nullable=False,
            server_default="requirement",
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "claims",
        sa.Column(
            "self_authored",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("claims", "self_authored", schema=APP_SCHEMA)
    op.drop_column("requirements", "item_type", schema=APP_SCHEMA)
