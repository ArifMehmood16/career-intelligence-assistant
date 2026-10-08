"""Populated call-progress upgrade preserves historical rows and enforces counts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.support.v2_http import analyse, sql_app

from career_assistant.adapters.persistence.migrate import alembic_config, upgrade_head
from career_assistant.settings import DatabaseSettings

pytestmark = pytest.mark.integration
SCHEMA = "career_assistant"
TASKS = f"{SCHEMA}.analysis_job_tasks"
COUNTERS = (
    "model_calls_done",
    "model_calls_total",
    "embedding_calls_done",
    "embedding_calls_total",
)
PRESERVED = (
    "analysis_job_tasks",
    "analysis_jobs",
    "documents",
    "score_explanations",
    "generated_drafts",
    "draft_citations",
)


def snapshot(session: Session, table: str) -> list[object]:
    subtraction = ""
    if table == "analysis_job_tasks":
        subtraction = "".join(f" - '{column}'" for column in COUNTERS)
    order = "position" if table == "analysis_job_tasks" else "id"
    return list(
        session.execute(
            text(
                f"SELECT to_jsonb(t){subtraction} FROM {SCHEMA}.{table} t "
                f"ORDER BY {order}"
            )
        ).scalars()
    )


def seed_tasks(session: Session, workspace: str, job: str) -> None:
    session.execute(text(f"DELETE FROM {TASKS}"))
    for position, (state, done, total) in enumerate(
        (
            ("pending", 0, None),
            ("running", 3, 8),
            ("done", 8, 8),
            ("skipped", 0, 0),
        )
    ):
        session.execute(
            text(
                f"INSERT INTO {TASKS} "
                "(job_id, workspace_id, key, position, state, units_done, "
                "units_total, started_at, finished_at) "
                "VALUES (:job, :ws, :key, :position, :state, "
                ":done, :total, :start, :end)"
            ),
            {
                "job": job,
                "ws": workspace,
                "key": f"historical-{state}",
                "position": position,
                "state": state,
                "done": done,
                "total": total,
                "start": None
                if position == 0
                else datetime(2026, 9, 1, 10, tzinfo=UTC),
                "end": datetime(2026, 9, 1, 10, 1, tzinfo=UTC)
                if position >= 2
                else None,
            },
        )


def assert_counter_constraints(session: Session) -> None:
    counters = session.execute(
        text(
            "SELECT model_calls_done, model_calls_total, embedding_calls_done, "
            f"embedding_calls_total FROM {TASKS} ORDER BY position"
        )
    ).all()
    assert counters == [(0, None, 0, None)] * 4
    for operation in ("model", "embedding"):
        update = text(
            f"UPDATE {TASKS} SET {operation}_calls_done=:done, "
            f"{operation}_calls_total=:total WHERE position=1"
        )
        for done, total in ((2, None), (2, 3), (3, 3)):
            session.execute(update, {"done": done, "total": total})
        for done, total in ((-1, None), (4, 3), (0, -1)):
            with pytest.raises(IntegrityError), session.begin_nested():
                session.execute(update, {"done": done, "total": total})


def test_populated_progress_upgrade_preserves_data_defaults_and_constraints(
    session_factory: sessionmaker[Session], database_settings: DatabaseSettings
) -> None:
    app = sql_app(session_factory)
    role, job = analyse(app)
    requirements = app.client.get(f"/api/roles/{role}/requirements").json()
    met = next(row for row in requirements if row["status"] == "met")
    generated = app.client.post(
        f"/api/roles/{role}/bullets", json={"requirementId": met["id"]}
    )
    assert generated.status_code == 200
    workspace = app.client.cookies["workspace"]
    url = database_settings.test_database_url
    try:
        command.downgrade(alembic_config(url), "c1f7a2d94e08")
        with session_factory() as session:
            seed_tasks(session, workspace, job)
            before = {table: snapshot(session, table) for table in PRESERVED}
            assert all(before.values())
            session.commit()
        command.upgrade(alembic_config(url), "b2d9c8e4f601")
        with session_factory() as session:
            assert {table: snapshot(session, table) for table in PRESERVED} == before
            assert_counter_constraints(session)
            session.commit()
    finally:
        upgrade_head(url)
