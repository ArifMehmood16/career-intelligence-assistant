"""Deleting the role or the CV stops its analysis: no further provider call.

The delete arrives while document calls are in flight. Already-started calls may
finish; nothing starts after deletion completes and no response is published.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Lock

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import BaseModel, SecretStr
from sqlalchemy.orm import Session, sessionmaker
from tests.support.structured_transport import StructuredTransport
from tests.support.v2_http import queue_role, sql_app

from career_assistant.adapters.persistence.analysis_worker import SqlAnalysisWorker
from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.provider_settings_store import (
    SqlProviderSettingsStore,
)
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.adapters.persistence.v2_worker import (
    V2JobRunner,
    V2Providers,
    V2RunnerConfig,
)
from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.adapters.providers.http_transport import HttpResponse
from career_assistant.application.analysis.v2 import V2Limits
from career_assistant.application.judge.cache import ModelIdentity
from career_assistant.application.ports.structured import (
    StructuredRequest,
    StructuredResult,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    EmbeddingRequest,
    EmbeddingResult,
)
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric_v2
from career_assistant.domain.jobs import AnalysisJob, JobStage
from career_assistant.main import create_app
from career_assistant.settings import ProviderSettings

pytestmark = pytest.mark.integration

RUBRIC = load_scoring_rubric_v2(
    Path(__file__).resolve().parents[3] / "config" / "scoring_rubric.toml"
)

_CV = """Experience
Senior Analytics Engineer — Acme — January 2022 – Present
- Owned dbt models in production for the warehouse.
"""

_JD = """Requirements
- Must have production dbt experience
"""

Delete = Callable[[TestClient, str], Response]


def _delete_role(client: TestClient, role_id: str) -> Response:
    return client.delete(f"/api/roles/{role_id}")


def _delete_cv(client: TestClient, role_id: str) -> Response:
    return client.delete("/api/cv")


_DELETES = pytest.mark.parametrize(
    "delete", [_delete_role, _delete_cv], ids=["role-deleted", "cv-deleted"]
)


def _stopped(client: TestClient, delete: Delete, job_id: str, role_id: str) -> None:
    """A deleted role takes its job; a deleted CV leaves it failed by name."""
    job = client.get(f"/api/jobs/{job_id}")
    if delete is _delete_role:
        assert job.status_code == 404
        return
    assert job.json()["state"] == "failed"
    assert job.json()["error"]["code"] == "cv_deleted"
    assert client.get(f"/api/roles/{role_id}").json()["status"] == "failed"


@dataclass
class _DeletingTransport:
    """Scripted chat completions; the first one triggers the delete."""

    on_first: Callable[[], Response]
    inner: StructuredTransport = field(default_factory=StructuredTransport)
    completions: int = 0
    after_delete: int = 0
    deleted: Event = field(default_factory=Event)
    lock: Lock = field(default_factory=Lock)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
        timeout_seconds: float,
    ) -> HttpResponse:
        if "/chat/completions" in url:
            with self.lock:
                self.completions += 1
                self.after_delete += int(self.deleted.is_set())
                first = self.completions == 1
            if first:
                response = self.on_first()
                assert response.status_code == 204
                self.deleted.set()
        return self.inner.request(
            method,
            url,
            headers=headers,
            json_body=json_body,
            timeout_seconds=timeout_seconds,
        )


@_DELETES
def test_hosted_analysis_makes_no_model_call_after_the_delete(
    session_factory: sessionmaker[Session], delete: Delete
) -> None:
    ids: dict[str, str] = {}
    transport = _DeletingTransport(on_first=lambda: delete(client, ids["role"]))
    settings = ProviderSettings(
        completion_provider="hermetic",
        embedding_provider="hermetic",
        allow_hosted_providers=True,
        openai_api_key=SecretStr("sk-test-never-leave-the-fixture"),
        openai_completion_model="gpt-4o-mini",
        openai_embedding_model="text-embedding-3-small",
    )

    def uow_factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    cv_store = SqlCvStore(uow_factory)
    worker = SqlAnalysisWorker(uow_factory, providers=settings, transport=transport)
    client = TestClient(
        create_app(
            providers=settings,
            cv_store=cv_store,
            role_store=SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory),
            provider_choice_store=SqlProviderSettingsStore(uow_factory),
        )
    )
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    client.put(
        "/api/settings/providers",
        json={
            "answerProviderId": "openai",
            "answerModel": "gpt-4o-mini",
            "indexProviderId": "hermetic",
            "indexModel": "lexical-hash-v1",
            "acknowledgedEgress": True,
        },
    )
    created = client.post(
        "/api/roles", json={"title": "AE", "company": "Acme", "description": _JD}
    ).json()
    ids["role"] = created["role"]["id"]

    worker.drain()

    # CV and JD may both have started before the deletion finishes.
    assert 1 <= transport.completions <= 2
    assert transport.deleted.is_set()
    assert transport.after_delete == 0
    _stopped(client, delete, created["jobId"], ids["role"])


class _CountingEmbedding:
    def __init__(self) -> None:
        self._inner = HermeticEmbeddingAdapter()
        self.calls = 0

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.calls += 1
        return self._inner.embed(request)


class _DeletingStructured:
    """Hermetic structured replies; the first call triggers the delete."""

    def __init__(self, on_first: Callable[[], object]) -> None:
        self._inner = HermeticStructuredCompleter()
        self._on_first = on_first
        self.calls = 0

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete_structured[T: BaseModel](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]:
        self.calls += 1
        if self.calls == 1:
            self._on_first()
        return self._inner.complete_structured(request)


def _no_failure(
    job: AnalysisJob, stage: JobStage, cause: BaseException | None
) -> AnalysisJob:
    raise AssertionError(f"a cancelled job was failed at {stage.value}") from cause


@_DELETES
def test_v2_makes_no_model_call_after_the_delete(
    session_factory: sessionmaker[Session], delete: Delete
) -> None:
    app = sql_app(session_factory)
    role_id, job_id = queue_role(app)
    structured = _DeletingStructured(lambda: delete(app.client, role_id))
    embedding = _CountingEmbedding()
    job = app.worker.claim_next()
    assert job is not None
    runner = V2JobRunner(
        app.uow_factory,
        providers=lambda _ws: V2Providers(
            structured=structured,
            embedding=embedding,
            judge_model=ModelIdentity("hermetic", "rules-v1"),
        ),
        config=V2RunnerConfig(
            rubric=RUBRIC,
            limits=V2Limits(max_rewrites=5, max_chars_per_text=8_000),
            clock=lambda: datetime.now(UTC),
        ),
        fail=_no_failure,
    )

    runner.run(job)

    assert (structured.calls, embedding.calls) == (1, 0)
    _stopped(app.client, delete, job_id, role_id)
