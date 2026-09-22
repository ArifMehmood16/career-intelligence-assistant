"""Persist claim detail, employment dates, and requirement seniority."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a7c4e1b90d33"
down_revision = "f5b0d3c29f12"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"


def upgrade() -> None:
    op.add_column(
        "requirements",
        sa.Column("seniority_signal", sa.String(length=64), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "claims",
        sa.Column(
            "employer", sa.String(length=256), nullable=False, server_default=""
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "claims",
        sa.Column("title", sa.String(length=256), nullable=False, server_default=""),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "claims",
        sa.Column("scope", sa.Text(), nullable=False, server_default=""),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "claims",
        sa.Column(
            "technologies",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "claims",
        sa.Column("outcome", sa.Text(), nullable=False, server_default=""),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "claims",
        sa.Column("extraction_confidence", sa.Float(), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "claims",
        sa.Column("period_start", sa.Date(), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "claims",
        sa.Column("period_end", sa.Date(), nullable=True),
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("claims", "period_end", schema=APP_SCHEMA)
    op.drop_column("claims", "period_start", schema=APP_SCHEMA)
    op.drop_column("claims", "extraction_confidence", schema=APP_SCHEMA)
    op.drop_column("claims", "outcome", schema=APP_SCHEMA)
    op.drop_column("claims", "technologies", schema=APP_SCHEMA)
    op.drop_column("claims", "scope", schema=APP_SCHEMA)
    op.drop_column("claims", "title", schema=APP_SCHEMA)
    op.drop_column("claims", "employer", schema=APP_SCHEMA)
    op.drop_column("requirements", "seniority_signal", schema=APP_SCHEMA)
