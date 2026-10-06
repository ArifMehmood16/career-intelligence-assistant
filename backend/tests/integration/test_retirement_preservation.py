"""Populated retirement upgrades preserve originals and current publications."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.support.retirement_seed import (
    HistoricalRole,
    historical_job,
    historical_role,
    historical_score,
)
from tests.support.v2_http import SqlApp, analyse, sql_app
from tests.support.v2_seed import seed_v2

from career_assistant.adapters.persistence.migrate import alembic_config, upgrade_head
from career_assistant.adapters.persistence.models import Base
from career_assistant.settings import DatabaseSettings

pytestmark = pytest.mark.integration
SCHEMA = "career_assistant"
LEGACY_TABLES = {
    "claims",
    "claim_spans",
    "requirements",
    "mappings",
    "mapping_spans",
    "embeddings",
}
PRESERVED_TABLES = (
    "documents",
    "spans",
    "chunks",
    "chunk_embeddings",
    "requirement_items",
    "kg_nodes",
    "kg_edges",
    "match_verdicts",
    "verdict_evidence",
    "retrieval_traces",
    "score_explanations",
    "generated_drafts",
    "draft_citations",
)


@dataclass(frozen=True)
class Upgraded:
    app: SqlApp
    current_role: str
    old_jobs: tuple[HistoricalRole, ...]
    controls: tuple[HistoricalRole, ...]
    retired_roles: tuple[str, ...]
    before: dict[str, list[object]]
    factory: sessionmaker[Session]


def _snapshot(session: Session) -> dict[str, list[object]]:
    return {
        table: list(
            session.execute(
                text(f"SELECT to_jsonb(t) FROM {SCHEMA}.{table} t ORDER BY id")
            ).scalars()
        )
        for table in PRESERVED_TABLES
    }


@pytest.fixture()
def upgraded(
    session_factory: sessionmaker[Session], database_settings: DatabaseSettings
) -> Iterator[Upgraded]:
    app = sql_app(session_factory)
    seed_v2(app.uow_factory(), session_factory)
    role, _ = analyse(app)
    requirements = app.client.get(f"/api/roles/{role}/requirements").json()
    met = next(row for row in requirements if row["status"] == "met")
    generated = app.client.post(
        f"/api/roles/{role}/bullets", json={"requirementId": met["id"]}
    )
    assert generated.status_code == 200, generated.text
    workspace = app.client.cookies["workspace"]
    with app.uow_factory() as uow:
        record = uow.roles.get(workspace, role)
        assert record is not None
        jd = record.job_description_document_id
    url = database_settings.test_database_url
    command.downgrade(alembic_config(url), "b2d9c8e4f601")
    try:
        with session_factory() as session:
            span = str(
                session.scalar(
                    text(
                        f"SELECT id FROM {SCHEMA}.spans "
                        "WHERE workspace_id=:ws ORDER BY id LIMIT 1"
                    ),
                    {"ws": workspace},
                )
            )
            invalidated = historical_role(
                session, workspace, jd, state="succeeded", pipeline="v2"
            )
            historical_score(session, workspace, invalidated.role, span, pipeline="v2")
            session.execute(
                text(
                    f"UPDATE {SCHEMA}.score_explanations "
                    "SET invalidated=TRUE WHERE role_id=:role"
                ),
                {"role": invalidated.role},
            )
            before = _snapshot(session)
            retired_roles = [invalidated.role]
            for pipeline in (None, "v1"):
                old = historical_role(session, workspace, jd, state="succeeded")
                historical_score(session, workspace, old.role, span, pipeline=pipeline)
                retired_roles.append(old.role)
            historical_score(session, workspace, role, span, version=0)
            old_jobs = tuple(
                historical_role(session, workspace, jd, state=state)
                for state in ("queued", "running")
            )
            # A retired reanalysis must not invalidate a valid previous publication.
            resumed = historical_job(
                session, workspace, role, state="running", pipeline="v1"
            )
            session.execute(
                text(f"UPDATE {SCHEMA}.roles SET status='analysing' WHERE id=:id"),
                {"id": role},
            )
            old_jobs += (HistoricalRole(role, resumed),)
            controls = tuple(
                historical_role(session, workspace, jd, state=state, pipeline="v2")
                for state in ("queued", "running")
            )
            for control in controls:
                old_jobs += (
                    HistoricalRole(
                        control.role,
                        historical_job(
                            session,
                            workspace,
                            control.role,
                            state="queued",
                            pipeline="v1",
                        ),
                    ),
                )
            session.commit()
        upgrade_head(url)
        yield Upgraded(
            app, role, old_jobs, controls, tuple(retired_roles), before, session_factory
        )
    finally:
        upgrade_head(url)


def test_retirement_preserves_originals_current_results_drafts_and_citations(
    upgraded: Upgraded,
) -> None:
    with upgraded.factory() as session:
        assert all(upgraded.before.values()), "all retained tables are populated"
        assert _snapshot(session) == upgraded.before
        statuses = dict(
            session.execute(text(f"SELECT id::text, status FROM {SCHEMA}.roles")).all()
        )
    assert statuses[upgraded.current_role] == "ready"
    assert all(statuses[role] == "failed" for role in upgraded.retired_roles)
    assert (
        upgraded.app.client.get(
            f"/api/roles/{upgraded.current_role}/verdicts"
        ).status_code
        == 200
    )


def test_retirement_ends_legacy_live_jobs_without_touching_current_jobs(
    upgraded: Upgraded,
) -> None:
    with upgraded.factory() as session:
        jobs = {
            str(row.id): row
            for row in session.execute(text(f"SELECT * FROM {SCHEMA}.analysis_jobs"))
        }
        statuses = dict(
            session.execute(text(f"SELECT id::text, status FROM {SCHEMA}.roles")).all()
        )
        tasks = set(
            session.execute(
                text(f"SELECT job_id::text FROM {SCHEMA}.analysis_job_tasks")
            ).scalars()
        )
    for old in upgraded.old_jobs:
        assert jobs[old.job].state == "failed", (
            "retired live requests must not restart or block current work"
        )
        assert jobs[old.job].error_code == "legacy_analysis_retired"
        assert jobs[old.job].finished_at is not None
        assert old.job not in tasks
        expected = "failed"
        if old.role == upgraded.current_role:
            expected = "ready"
        elif old.role in {control.role for control in upgraded.controls}:
            expected = "analysing"
        assert statuses[old.role] == expected
    for current, expected in zip(upgraded.controls, ("queued", "running"), strict=True):
        assert jobs[current.job].state == expected
        assert jobs[current.job].error_code is None
        assert jobs[current.job].finished_at is None
        assert current.job in tasks
        assert statuses[current.role] == "analysing"


def test_retirement_removes_storage_selector_and_disallows_v1_jobs(
    upgraded: Upgraded,
) -> None:
    with upgraded.factory() as session:
        tables = set(
            session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema=:s"
                ),
                {"s": SCHEMA},
            ).scalars()
        )
        columns = set(
            session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema=:s AND table_name='workspaces'"
                ),
                {"s": SCHEMA},
            ).scalars()
        )
        assert not tables & LEGACY_TABLES
        assert tables == {table.name for table in Base.metadata.sorted_tables}
        assert "pipeline_version" not in columns
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    f"UPDATE {SCHEMA}.analysis_jobs "
                    "SET pipeline_version='v1' WHERE id=:id"
                ),
                {"id": upgraded.controls[0].job},
            )
        session.rollback()
