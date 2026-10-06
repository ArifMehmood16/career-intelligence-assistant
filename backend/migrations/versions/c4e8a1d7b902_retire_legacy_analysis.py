"""Retire legacy matching storage and the workspace architecture selector.

Original documents and the current chunks, graphs and verdicts remain. Legacy
scores and their drafts are invalidated; affected roles can be reanalysed using
the current architecture. Downgrade restores the historical schema, not erased
legacy data. Verification applies this revision only to disposable test storage.
Already-applied upgrades cannot recover the overwritten legacy job identity.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision = "c4e8a1d7b902"
down_revision = "b2d9c8e4f601"
branch_labels = None
depends_on = None
APP_SCHEMA = "career_assistant"


def upgrade() -> None:
    op.execute(f"""
        DELETE FROM {APP_SCHEMA}.generated_drafts AS draft
        USING {APP_SCHEMA}.score_explanations AS score
        WHERE draft.workspace_id = score.workspace_id
          AND draft.role_id = score.role_id
          AND draft.analysis_version = score.analysis_version
          AND COALESCE(score.explanation->>'pipeline_version', '') <> 'v2'
    """)
    op.execute(f"""
        DELETE FROM {APP_SCHEMA}.score_explanations
        WHERE COALESCE(explanation->>'pipeline_version', '') <> 'v2'
    """)
    op.execute(f"""
        UPDATE {APP_SCHEMA}.roles AS role SET status = 'failed'
        WHERE role.status = 'ready' AND NOT EXISTS (
            SELECT 1 FROM {APP_SCHEMA}.score_explanations AS score
            WHERE score.workspace_id = role.workspace_id
              AND score.role_id = role.id
              AND score.analysis_version = role.analysis_version
              AND score.invalidated IS FALSE
        )
    """)
    _retire_live_jobs()
    for table in ("mapping_spans", "mappings", "claim_spans", "claims", "requirements", "embeddings"):
        op.drop_table(table, schema=APP_SCHEMA)
    op.drop_constraint(
        op.f('ck_workspaces_pipeline_version'),
        'workspaces',
        type_='check',
        schema=APP_SCHEMA,
    )
    op.drop_column("workspaces", "pipeline_version", schema=APP_SCHEMA)
    op.drop_constraint(
        op.f('ck_analysis_jobs_pipeline_version'),
        'analysis_jobs',
        type_='check',
        schema=APP_SCHEMA,
    )
    op.execute(f"""
        DELETE FROM {APP_SCHEMA}.analysis_job_tasks
        WHERE job_id IN (
            SELECT id FROM {APP_SCHEMA}.analysis_jobs WHERE pipeline_version = 'v1'
        )
    """)
    op.execute(f"UPDATE {APP_SCHEMA}.analysis_jobs SET pipeline_version = 'v2'")
    op.alter_column(
        'analysis_jobs',
        'pipeline_version',
        server_default='v2',
        schema=APP_SCHEMA,
    )
    op.create_check_constraint(
        op.f('ck_analysis_jobs_pipeline_version'),
        'analysis_jobs',
        "pipeline_version = 'v2'",
        schema=APP_SCHEMA,
    )


def _retire_live_jobs() -> None:
    # Resolve roles before the old pipeline marker and live-job state disappear.
    # A concurrent current request retains ownership of its analysing role.
    op.execute(f"""
        UPDATE {APP_SCHEMA}.roles AS role
        SET status = CASE WHEN EXISTS (
            SELECT 1 FROM {APP_SCHEMA}.score_explanations AS score
            WHERE score.workspace_id = role.workspace_id
              AND score.role_id = role.id
              AND score.analysis_version = role.analysis_version
              AND score.invalidated IS FALSE
        ) THEN 'ready' ELSE 'failed' END
        WHERE role.status = 'analysing' AND EXISTS (
            SELECT 1 FROM {APP_SCHEMA}.analysis_jobs AS job
            WHERE job.workspace_id = role.workspace_id AND job.role_id = role.id
              AND job.pipeline_version = 'v1' AND job.state IN ('queued', 'running')
        ) AND NOT EXISTS (
            SELECT 1 FROM {APP_SCHEMA}.analysis_jobs AS job
            WHERE job.workspace_id = role.workspace_id AND job.role_id = role.id
              AND job.pipeline_version = 'v2' AND job.state IN ('queued', 'running')
        )
    """)
    op.execute(f"""
        UPDATE {APP_SCHEMA}.analysis_jobs
        SET state = 'failed', finished_at = CURRENT_TIMESTAMP,
            error_code = 'legacy_analysis_retired',
            error_message = 'This analysis was retired. Run a new analysis.'
        WHERE pipeline_version = 'v1' AND state IN ('queued', 'running')
    """)


def downgrade() -> None:
    op.drop_constraint(
        op.f('ck_analysis_jobs_pipeline_version'),
        'analysis_jobs',
        type_='check',
        schema=APP_SCHEMA,
    )
    op.alter_column(
        'analysis_jobs',
        'pipeline_version',
        server_default='v1',
        schema=APP_SCHEMA,
    )
    op.create_check_constraint(
        op.f('ck_analysis_jobs_pipeline_version'),
        'analysis_jobs',
        "pipeline_version IN ('v1', 'v2')",
        schema=APP_SCHEMA,
    )
    op.add_column(
        'workspaces',
        sa.Column('pipeline_version', sa.String(8), nullable=False, server_default='v2'),
        schema=APP_SCHEMA,
    )
    op.create_check_constraint(
        op.f('ck_workspaces_pipeline_version'),
        'workspaces',
        "pipeline_version IN ('v1', 'v2')",
        schema=APP_SCHEMA,
    )
    op.create_table(
        'claims',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('competency', sa.String(length=128), nullable=False),
        sa.Column('context', sa.Text(), nullable=False),
        sa.Column('duration_signal', sa.String(length=64), nullable=True),
        sa.Column('recency_signal', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ['document_id'],
            ['career_assistant.documents.id'],
            name=op.f('fk_claims_document_id_documents'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['workspace_id'],
            ['career_assistant.workspaces.id'],
            name=op.f('fk_claims_workspace_id_workspaces'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_claims')),
        schema=APP_SCHEMA,
    )
    op.create_index(
        'ix_claims_workspace_id',
        'claims',
        ['workspace_id'],
        unique=False,
        schema=APP_SCHEMA,
    )
    op.create_table(
        'claim_spans',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('claim_id', sa.UUID(), nullable=False),
        sa.Column('span_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ['claim_id'],
            ['career_assistant.claims.id'],
            name=op.f('fk_claim_spans_claim_id_claims'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['span_id'],
            ['career_assistant.spans.id'],
            name=op.f('fk_claim_spans_span_id_spans'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['workspace_id'],
            ['career_assistant.workspaces.id'],
            name=op.f('fk_claim_spans_workspace_id_workspaces'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_claim_spans')),
        sa.UniqueConstraint('claim_id', 'span_id', name='uq_claim_spans_pair'),
        schema=APP_SCHEMA,
    )
    op.create_index(
        'ix_claim_spans_workspace_id',
        'claim_spans',
        ['workspace_id'],
        unique=False,
        schema=APP_SCHEMA,
    )
    op.create_table(
        'requirements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('competency', sa.String(length=128), nullable=False),
        sa.Column('must_have', sa.Boolean(), nullable=False),
        sa.Column('source_span_id', sa.UUID(), nullable=True),
        sa.Column('extraction_confidence', sa.Float(), nullable=True),
        sa.Column('is_vague', sa.Boolean(), nullable=False),
        sa.Column('analysis_version', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['role_id'],
            ['career_assistant.roles.id'],
            name=op.f('fk_requirements_role_id_roles'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['source_span_id'],
            ['career_assistant.spans.id'],
            name=op.f('fk_requirements_source_span_id_spans'),
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['workspace_id'],
            ['career_assistant.workspaces.id'],
            name=op.f('fk_requirements_workspace_id_workspaces'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_requirements')),
        schema=APP_SCHEMA,
    )
    op.create_index(
        'ix_requirements_workspace_id',
        'requirements',
        ['workspace_id'],
        unique=False,
        schema=APP_SCHEMA,
    )
    op.create_table(
        'mappings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('requirement_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('reason_code', sa.String(length=64), nullable=False),
        sa.Column('analysis_version', sa.Integer(), nullable=False),
        sa.Column('invalidated', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ['requirement_id'],
            ['career_assistant.requirements.id'],
            name=op.f('fk_mappings_requirement_id_requirements'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['role_id'],
            ['career_assistant.roles.id'],
            name=op.f('fk_mappings_role_id_roles'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['workspace_id'],
            ['career_assistant.workspaces.id'],
            name=op.f('fk_mappings_workspace_id_workspaces'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_mappings')),
        sa.UniqueConstraint(
            'role_id',
            'requirement_id',
            'analysis_version',
            name='uq_mappings_role_requirement_version',
        ),
        schema=APP_SCHEMA,
    )
    op.create_index(
        'ix_mappings_workspace_id',
        'mappings',
        ['workspace_id'],
        unique=False,
        schema=APP_SCHEMA,
    )
    op.create_table(
        'mapping_spans',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('mapping_id', sa.UUID(), nullable=False),
        sa.Column('span_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ['mapping_id'],
            ['career_assistant.mappings.id'],
            name=op.f('fk_mapping_spans_mapping_id_mappings'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['span_id'],
            ['career_assistant.spans.id'],
            name=op.f('fk_mapping_spans_span_id_spans'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['workspace_id'],
            ['career_assistant.workspaces.id'],
            name=op.f('fk_mapping_spans_workspace_id_workspaces'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_mapping_spans')),
        sa.UniqueConstraint('mapping_id', 'span_id', name='uq_mapping_spans_pair'),
        schema=APP_SCHEMA,
    )
    op.create_index(
        'ix_mapping_spans_workspace_id',
        'mapping_spans',
        ['workspace_id'],
        unique=False,
        schema=APP_SCHEMA,
    )
    op.create_table(
        'embeddings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('owner_kind', sa.String(length=16), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('model_tag', sa.String(length=128), nullable=False),
        sa.Column('dimensions', sa.Integer(), nullable=False),
        sa.Column('text_sha256', sa.String(length=64), nullable=False),
        sa.Column('embedding', VECTOR(), nullable=False),
        sa.CheckConstraint(
            "owner_kind IN ('requirement', 'claim')",
            name=op.f('ck_embeddings_embedding_owner_kind'),
        ),
        sa.ForeignKeyConstraint(
            ['workspace_id'],
            [f'{APP_SCHEMA}.workspaces.id'],
            name=op.f('fk_embeddings_workspace_id_workspaces'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_embeddings')),
        sa.UniqueConstraint(
            'workspace_id',
            'owner_kind',
            'owner_id',
            'provider',
            'model_tag',
            'text_sha256',
            name='uq_embeddings_owner_provider_text',
        ),
        schema=APP_SCHEMA,
    )
    op.create_index(
        'ix_embeddings_workspace_id',
        'embeddings',
        ['workspace_id'],
        unique=False,
        schema=APP_SCHEMA,
    )
    op.add_column(
        'mappings',
        sa.Column('signals', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        'requirements',
        sa.Column(
            'item_type',
            sa.String(length=32),
            nullable=False,
            server_default='requirement',
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        'claims',
        sa.Column(
            'self_authored',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        'requirements',
        sa.Column('seniority_signal', sa.String(length=64), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        'claims',
        sa.Column('employer', sa.String(length=256), nullable=False, server_default=''),
        schema=APP_SCHEMA,
    )
    op.add_column(
        'claims',
        sa.Column('title', sa.String(length=256), nullable=False, server_default=''),
        schema=APP_SCHEMA,
    )
    op.add_column(
        'claims',
        sa.Column('scope', sa.Text(), nullable=False, server_default=''),
        schema=APP_SCHEMA,
    )
    op.add_column(
        'claims',
        sa.Column(
            'technologies',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        schema=APP_SCHEMA,
    )
    op.add_column(
        'claims',
        sa.Column('outcome', sa.Text(), nullable=False, server_default=''),
        schema=APP_SCHEMA,
    )
    op.add_column(
        'claims',
        sa.Column('extraction_confidence', sa.Float(), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        'claims',
        sa.Column('period_start', sa.Date(), nullable=True),
        schema=APP_SCHEMA,
    )
    op.add_column(
        'claims',
        sa.Column('period_end', sa.Date(), nullable=True),
        schema=APP_SCHEMA,
    )
    for table in ("claims", "claim_spans", "requirements", "mappings", "mapping_spans", "embeddings"):
        op.execute(f"ALTER TABLE {APP_SCHEMA}.{table} ENABLE ROW LEVEL SECURITY")
