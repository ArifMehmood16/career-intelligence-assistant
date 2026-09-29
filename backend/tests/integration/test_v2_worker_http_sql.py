"""PLAN 18.10 — a v2 workspace's analysis runs the v2 pipeline end to end."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.support.v2_http import analyse, sql_app

from career_assistant.adapters.persistence.models import AnalysisJobRow
from career_assistant.api.deps import WORKSPACE_COOKIE

pytestmark = pytest.mark.integration


def _job_pipeline(session_factory: sessionmaker[Session], job_id: str) -> str:
    with session_factory() as session:
        return session.scalars(
            select(AnalysisJobRow.pipeline_version).where(
                AnalysisJobRow.id == uuid.UUID(job_id)
            )
        ).one()


def test_a_v2_workspace_is_analysed_and_scored_by_the_v2_pipeline(
    session_factory: sessionmaker[Session],
) -> None:
    app = sql_app(session_factory)
    client = app.client
    client.put("/api/settings/pipeline", json={"pipelineVersion": "v2"})

    role_id, job_id = analyse(app)

    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["state"] == "succeeded", job
    role = client.get(f"/api/roles/{role_id}").json()
    assert role["status"] == "ready"
    assert _job_pipeline(session_factory, job_id) == "v2"
    workspace = client.cookies[WORKSPACE_COOKIE]
    with app.uow_factory() as uow:
        result = uow.v2.result(workspace, role_id)
    assert result is not None
    assert result.analysis_id == job_id
    assert result.verdicts
    assert role["fitScore"] == round(result.score)


def test_a_default_workspace_still_runs_v1(
    session_factory: sessionmaker[Session],
) -> None:
    app = sql_app(session_factory)

    role_id, job_id = analyse(app)

    assert app.client.get(f"/api/jobs/{job_id}").json()["state"] == "succeeded"
    assert _job_pipeline(session_factory, job_id) == "v1"
    with app.uow_factory() as uow:
        assert uow.v2.result(app.client.cookies[WORKSPACE_COOKIE], role_id) is None
