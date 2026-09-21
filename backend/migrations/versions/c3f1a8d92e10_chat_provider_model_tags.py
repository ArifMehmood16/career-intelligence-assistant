"""Add answer kind and selected model tags on provider_settings."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c3f1a8d92e10"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"


def upgrade() -> None:
    op.add_column(
        "answers",
        sa.Column(
            "kind",
            sa.String(length=32),
            nullable=False,
            server_default="answer",
        ),
        schema=APP_SCHEMA,
    )
    op.execute(
        sa.text(
            "ALTER TABLE career_assistant.answers "
            "ADD CONSTRAINT ck_answers_answer_kind "
            "CHECK (kind IN ('answer', 'insufficient'))"
        )
    )
    op.add_column(
        "provider_settings",
        sa.Column(
            "completion_model",
            sa.String(length=128),
            nullable=False,
            server_default="",
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "provider_settings",
        sa.Column(
            "embedding_model",
            sa.String(length=128),
            nullable=False,
            server_default="",
        ),
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE career_assistant.answers "
            "DROP CONSTRAINT IF EXISTS ck_answers_ck_answers_answer_kind"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE career_assistant.answers "
            "DROP CONSTRAINT IF EXISTS ck_answers_answer_kind"
        )
    )
    op.drop_column("provider_settings", "embedding_model", schema=APP_SCHEMA)
    op.drop_column("provider_settings", "completion_model", schema=APP_SCHEMA)
    op.drop_column("answers", "kind", schema=APP_SCHEMA)
