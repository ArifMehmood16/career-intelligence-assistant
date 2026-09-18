"""Add immutable draft versioning and groundedness provenance columns."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "71f0c6b9147f"
down_revision = "34b3a0846d82"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"


def upgrade() -> None:
    op.add_column(
        "generated_drafts",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "generated_drafts",
        sa.Column(
            "groundedness",
            sa.String(length=16),
            nullable=False,
            server_default="pass",
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "generated_drafts",
        sa.Column(
            "used_template_fallback",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "generated_drafts",
        sa.Column(
            "regeneration_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        schema=APP_SCHEMA,
    )
    op.create_unique_constraint(
        "uq_generated_drafts_role_kind_version",
        "generated_drafts",
        ["role_id", "kind", "version"],
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_generated_drafts_role_kind_version",
        "generated_drafts",
        schema=APP_SCHEMA,
        type_="unique",
    )
    op.drop_column("generated_drafts", "regeneration_count", schema=APP_SCHEMA)
    op.drop_column("generated_drafts", "used_template_fallback", schema=APP_SCHEMA)
    op.drop_column("generated_drafts", "groundedness", schema=APP_SCHEMA)
    op.drop_column("generated_drafts", "version", schema=APP_SCHEMA)
