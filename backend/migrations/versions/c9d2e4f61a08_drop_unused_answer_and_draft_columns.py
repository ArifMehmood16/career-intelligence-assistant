"""Drop unused answer usage columns and draft soft-invalidation.

Answers never store token/latency counts (those live in
provider_call_accounting). Generated drafts are hard-deleted on CV replace
instead of soft-invalidated, so the unused invalidated flag goes with them.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c9d2e4f61a08"
down_revision = "b8e5f2a01c44"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"


def upgrade() -> None:
    op.drop_column("answers", "prompt_tokens", schema=APP_SCHEMA)
    op.drop_column("answers", "completion_tokens", schema=APP_SCHEMA)
    op.drop_column("answers", "latency_ms", schema=APP_SCHEMA)
    op.drop_column("generated_drafts", "invalidated", schema=APP_SCHEMA)


def downgrade() -> None:
    op.add_column(
        "generated_drafts",
        sa.Column(
            "invalidated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "answers",
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "answers",
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        "answers",
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        schema=APP_SCHEMA,
    )
