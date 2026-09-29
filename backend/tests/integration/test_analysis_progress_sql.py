"""The worker records every task of a v1 or v2 analysis as it runs."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.support.refusing_structured import RefusingJudge
from tests.support.v2_http import SqlApp, analyse, queue_role, sql_app

from career_assistant.adapters.persistence.v2_worker import (
    V2JobRunner,
    V2Providers,
    V2RunnerConfig,
)
from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.application.analysis.v2 import V2Limits
from career_assistant.application.judge.cache import ModelIdentity
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric_v2
from career_assistant.domain.progress import JobTask, TaskKey, TaskState

pytestmark = pytest.mark.integration

_FINISHED = {TaskState.DONE, TaskState.SKIPPED}
RUBRIC = load_scoring_rubric_v2(
    Path(__file__).resolve().parents[3] / "config" / "scoring_rubric.toml"
)


def _tasks(app: SqlApp, job_id: str) -> tuple[JobTask, ...]:
    workspace = app.client.cookies["workspace"]
    with app.uow_factory() as uow:
        return uow.job_tasks.for_job(workspace, job_id)


def test_a_v1_analysis_finishes_every_task_in_order(
    session_factory: sessionmaker[Session],
) -> None:
    app = sql_app(session_factory)

    _role_id, job_id = analyse(app)

    tasks = _tasks(app, job_id)
    assert [t.key for t in tasks] == [
        TaskKey.PREPARE,
        TaskKey.READ_ADVERT,
        TaskKey.READ_CV,
        TaskKey.MATCH,
        TaskKey.SCORE,
    ]
    assert all(t.state is TaskState.DONE for t in tasks)
    assert all(t.started_at and t.finished_at for t in tasks)
    starts = [t.started_at for t in tasks]
    assert starts == sorted(starts)  # type: ignore[type-var]


def test_a_v2_analysis_counts_its_requirements(
    session_factory: sessionmaker[Session],
) -> None:
    app = sql_app(session_factory)
    app.client.put("/api/settings/pipeline", json={"pipelineVersion": "v2"})

    role_id, job_id = analyse(app)

    tasks = {t.key: t for t in _tasks(app, job_id)}
    assert list(tasks) == [
        TaskKey.PREPARE,
        TaskKey.READ_CV,
        TaskKey.READ_ADVERT,
        TaskKey.SEARCH,
        TaskKey.JUDGE,
        TaskKey.RECHECK,
        TaskKey.SCORE,
    ]
    assert {t.state for t in tasks.values()} <= _FINISHED
    verdicts = app.client.get(f"/api/roles/{role_id}/verdicts").json()
    judged = len(verdicts["verdicts"])
    assert judged > 0
    assert (tasks[TaskKey.JUDGE].units_done, tasks[TaskKey.JUDGE].units_total) == (
        judged,
        judged,
    )
    assert tasks[TaskKey.SEARCH].units_total == judged


def test_an_unscored_v2_analysis_stops_on_the_task_it_failed_in(
    session_factory: sessionmaker[Session],
) -> None:
    app = sql_app(session_factory)
    app.client.put("/api/settings/pipeline", json={"pipelineVersion": "v2"})
    _role_id, job_id = queue_role(app)
    job = app.worker.claim_next()
    assert job is not None
    runner = V2JobRunner(
        app.uow_factory,
        providers=lambda _ws: V2Providers(
            structured=RefusingJudge(),
            embedding=HermeticEmbeddingAdapter(),
            judge_model=ModelIdentity("hermetic", "rules-v1"),
        ),
        config=V2RunnerConfig(
            rubric=RUBRIC,
            limits=V2Limits(max_rewrites=5, max_chars_per_text=8_000),
            clock=lambda: datetime.now(UTC),
        ),
        fail=lambda job, stage, cause: job,
    )

    finished = runner.run(job)

    assert finished.error is not None
    tasks = {t.key: t for t in _tasks(app, job_id)}
    assert tasks[TaskKey.SCORE].state is TaskState.RUNNING
    assert tasks[TaskKey.JUDGE].state is TaskState.DONE
