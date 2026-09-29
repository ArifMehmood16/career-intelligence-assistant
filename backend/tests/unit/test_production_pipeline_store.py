"""PLAN 18.10 — the production app keeps the pipeline choice in PostgreSQL."""

from __future__ import annotations

from career_assistant.adapters.persistence.pipeline_store import (
    SqlPipelineVersionStore,
)
from career_assistant.main import create_production_app


def test_production_app_uses_the_sql_pipeline_store() -> None:
    app = create_production_app()

    assert isinstance(app.state.pipeline_store, SqlPipelineVersionStore)
