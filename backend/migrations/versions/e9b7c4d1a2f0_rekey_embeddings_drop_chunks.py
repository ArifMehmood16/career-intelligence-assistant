"""Drop unused chunks; re-key embeddings to requirement/claim owners."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR

revision = "e9b7c4d1a2f0"
down_revision = "c3f1a8d92e10"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"


def upgrade() -> None:
    op.drop_index(
        "ix_embeddings_workspace_id",
        table_name="embeddings",
        schema=APP_SCHEMA,
    )
    op.drop_table("embeddings", schema=APP_SCHEMA)
    op.drop_index("ix_chunks_workspace_id", table_name="chunks", schema=APP_SCHEMA)
    op.drop_table("chunks", schema=APP_SCHEMA)

    op.create_table(
        "embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("owner_kind", sa.String(length=16), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_tag", sa.String(length=128), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("text_sha256", sa.String(length=64), nullable=False),
        sa.Column("embedding", VECTOR(), nullable=False),
        sa.CheckConstraint(
            "owner_kind IN ('requirement', 'claim')",
            name="ck_embeddings_embedding_owner_kind",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            [f"{APP_SCHEMA}.workspaces.id"],
            name=op.f("fk_embeddings_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_embeddings")),
        sa.UniqueConstraint(
            "workspace_id",
            "owner_kind",
            "owner_id",
            "provider",
            "model_tag",
            "text_sha256",
            name="uq_embeddings_owner_provider_text",
        ),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_embeddings_workspace_id",
        "embeddings",
        ["workspace_id"],
        unique=False,
        schema=APP_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_embeddings_workspace_id",
        table_name="embeddings",
        schema=APP_SCHEMA,
    )
    op.drop_table("embeddings", schema=APP_SCHEMA)

    op.create_table(
        "chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            [f"{APP_SCHEMA}.documents.id"],
            name=op.f("fk_chunks_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            [f"{APP_SCHEMA}.workspaces.id"],
            name=op.f("fk_chunks_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chunks")),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_chunks_workspace_id",
        "chunks",
        ["workspace_id"],
        unique=False,
        schema=APP_SCHEMA,
    )
    op.create_table(
        "embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_tag", sa.String(length=128), nullable=False),
        sa.Column("left_machine", sa.Boolean(), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", VECTOR(dim=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            [f"{APP_SCHEMA}.chunks.id"],
            name=op.f("fk_embeddings_chunk_id_chunks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            [f"{APP_SCHEMA}.workspaces.id"],
            name=op.f("fk_embeddings_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_embeddings")),
        schema=APP_SCHEMA,
    )
    op.create_index(
        "ix_embeddings_workspace_id",
        "embeddings",
        ["workspace_id"],
        unique=False,
        schema=APP_SCHEMA,
    )
