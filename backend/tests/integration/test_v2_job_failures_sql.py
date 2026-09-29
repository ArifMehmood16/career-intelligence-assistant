"""PLAN 18.10 — an incomplete v2 analysis fails its job and publishes no score."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.support.refusing_structured import InvalidCvChunker, RefusingJudge
from tests.support.v2_http import SqlApp, queue_role, sql_app

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
from career_assistant.application.ports.structured import StructuredCompletionPort
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric_v2
from career_assistant.domain.jobs import AnalysisJob, JobStage

pytestmark = pytest.mark.integration

RUBRIC = load_scoring_rubric_v2(
    Path(__file__).resolve().parents[3] / "config" / "scoring_rubric.toml"
)


def _unexpected(
    job: AnalysisJob, stage: JobStage, cause: BaseException | None
) -> AnalysisJob:
    raise AssertionError(f"unexpected failure at {stage.value}") from cause


def _run(app: SqlApp, structured: StructuredCompletionPort) -> AnalysisJob:
    job = app.worker.claim_next()
    assert job is not None
    runner = V2JobRunner(
        app.uow_factory,
        providers=lambda _ws: V2Providers(
            structured=structured,
            embedding=HermeticEmbeddingAdapter(),
            judge_model=ModelIdentity("hermetic", "rules-v1"),
        ),
        config=V2RunnerConfig(
            rubric=RUBRIC,
            limits=V2Limits(max_rewrites=5, max_chars_per_text=8_000),
            clock=lambda: datetime.now(UTC),
        ),
        fail=_unexpected,
    )
    return runner.run(job)


@pytest.mark.parametrize(
    ("structured", "code"),
    [
        (RefusingJudge(), "assessment_incomplete"),
        (InvalidCvChunker(), "extraction_incomplete"),
    ],
    ids=["judge-refuses", "chunker-invalid"],
)
def test_an_incomplete_v2_analysis_publishes_no_score(
    session_factory: sessionmaker[Session],
    structured: StructuredCompletionPort,
    code: str,
) -> None:
    app = sql_app(session_factory)
    app.client.put("/api/settings/pipeline", json={"pipelineVersion": "v2"})
    role_id, job_id = queue_role(app)

    finished = _run(app, structured)

    assert finished.error is not None
    assert finished.error.code == code
    job = app.client.get(f"/api/jobs/{job_id}").json()
    assert job["state"] == "failed"
    assert job["error"]["code"] == code
    role = app.client.get(f"/api/roles/{role_id}").json()
    assert role["status"] == "failed"
    assert role["fitScore"] == 0
    verdicts = app.client.get(f"/api/roles/{role_id}/verdicts")
    assert verdicts.status_code == 409
