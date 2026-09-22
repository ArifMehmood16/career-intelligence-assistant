"""Persist who assessed an analysis, and whether that assessment failed."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b8e5f2a01c44"
down_revision = "a7c4e1b90d33"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"


def upgrade() -> None:
    op.add_column(
        "score_explanations",
        sa.Column(
            "assessment_provider",
            sa.String(length=64),
            nullable=False,
            server_default="hermetic",
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "score_explanations",
        sa.Column(
            "assessment_model",
            sa.String(length=128),
            nullable=False,
            server_default="rules-v1",
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "score_explanations",
        sa.Column(
            "prompt_version",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "score_explanations",
        sa.Column(
            "rubric_version",
            sa.String(length=64),
            nullable=False,
            server_default="scoring-rubric-v1",
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "score_explanations",
        sa.Column(
            "left_machine",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "score_explanations",
        sa.Column("failure_status", sa.String(length=64), nullable=True),
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("score_explanations", "failure_status", schema=APP_SCHEMA)
    op.drop_column("score_explanations", "left_machine", schema=APP_SCHEMA)
    op.drop_column("score_explanations", "rubric_version", schema=APP_SCHEMA)
    op.drop_column("score_explanations", "prompt_version", schema=APP_SCHEMA)
    op.drop_column("score_explanations", "assessment_model", schema=APP_SCHEMA)
    op.drop_column("score_explanations", "assessment_provider", schema=APP_SCHEMA)
