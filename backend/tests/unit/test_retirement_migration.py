"""Retirement DDL must respect the application's constraint naming convention."""

from __future__ import annotations

import importlib.util
from io import StringIO
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

from career_assistant.adapters.persistence.models import Base

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations/versions/c4e8a1d7b902_retire_legacy_analysis.py"
)


def _migration_sql(direction: str) -> str:
    spec = importlib.util.spec_from_file_location("retirement_migration", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql",
        opts={
            "as_sql": True,
            "output_buffer": output,
            "target_metadata": Base.metadata,
        },
    )
    with Operations.context(context):
        getattr(module, direction)()
    return output.getvalue()


@pytest.mark.parametrize("direction", ["upgrade", "downgrade"])
def test_pipeline_constraints_use_the_existing_names(direction: str) -> None:
    sql = _migration_sql(direction)

    assert "CONSTRAINT ck_workspaces_pipeline_version" in sql
    assert "CONSTRAINT ck_analysis_jobs_pipeline_version" in sql
    assert "ck_workspaces_ck_" not in sql
    assert "ck_analysis_jobs_ck_" not in sql


def test_downgrade_restores_the_historical_embedding_constraint_name() -> None:
    sql = _migration_sql("downgrade")

    assert "CONSTRAINT ck_embeddings_embedding_owner_kind CHECK" in sql
    assert "ck_embeddings_ck_" not in sql
