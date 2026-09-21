"""Phase 13A.10 — persist mapping embeddings and honour the egress gate."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker
from tests.support.scripted_transport import ScriptedTransport

from career_assistant.adapters.persistence.analysis_worker import SqlAnalysisWorker
from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.provider_settings_store import (
    SqlProviderSettingsStore,
)
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    EmbeddingRequest,
    EmbeddingResult,
)
from career_assistant.application.providers.catalogue import ProviderChoice
from career_assistant.domain.jobs import JobState
from career_assistant.main import create_app
from career_assistant.settings import ProviderSettings

pytestmark = pytest.mark.integration

_CV = """Experience
Senior Analytics Engineer — Acme — 2022-01 — Present
- Owned dbt models in production for the warehouse.
"""

_JD = """Requirements
- Must have production dbt experience
"""


@dataclass
class _CountingEmbedding:
    calls: list[tuple[str, ...]] = field(default_factory=list)
    provider_id: str = "scripted"
    model_tag: str = "scripted-v1"
    dimensions: int = 4

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id=self.provider_id,
            supports_completion=False,
            supports_embedding=True,
            supports_structured_output=False,
            context_window_tokens=8192,
            max_output_tokens=0,
            embedding_dimensions=self.dimensions,
            leaves_machine=False,
        )

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.calls.append(request.texts)
        unit = (1.0,) + (0.0,) * (self.dimensions - 1)
        return EmbeddingResult(
            vectors=tuple(unit for _ in request.texts),
            provider_id=self.provider_id,
            model_tag=self.model_tag,
            dimensions=self.dimensions,
            left_machine=False,
            input_tokens=len(request.texts),
            latency_ms=1,
        )


def _uow_factory(session_factory: sessionmaker[Session]):
    def factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    return factory


def _sql_client(
    session_factory: sessionmaker[Session],
    *,
    worker: SqlAnalysisWorker,
    providers: ProviderSettings | None = None,
) -> TestClient:
    uow_factory = _uow_factory(session_factory)
    cv_store = SqlCvStore(uow_factory)
    return TestClient(
        create_app(
            providers=providers,
            cv_store=cv_store,
            role_store=SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory),
            provider_choice_store=SqlProviderSettingsStore(uow_factory),
            analysis_worker=worker,
        )
    )


def test_embeddings_persist_provider_model_and_unconstrained_dimensions(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = _uow_factory(session_factory)
    worker = SqlAnalysisWorker(uow_factory)
    client = _sql_client(session_factory, worker=worker)
    uploaded = client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    assert uploaded.status_code == 201
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    assert created.status_code == 202
    done = worker.process_next()
    assert done is not None
    assert done.state is JobState.SUCCEEDED

    workspace_id = client.cookies["workspace"]
    with uow_factory() as uow:
        rows = uow.embeddings.list_for_workspace(workspace_id)
        assert rows
        assert all(row.provider == "hermetic" for row in rows)
        assert all(row.model_tag == "lexical-hash-v1" for row in rows)
        assert all(row.dimensions == 64 for row in rows)
        assert all(row.owner_kind in {"requirement", "claim"} for row in rows)

        wide = tuple(0.0 for _ in range(1535)) + (1.0,)
        owner_id = str(uuid.uuid4())
        uow.embeddings.put(
            workspace_id,
            owner_kind="claim",
            owner_id=owner_id,
            provider="openai",
            model_tag="text-embedding-3-small",
            text_sha256="a" * 64,
            dimensions=1536,
            vector=wide,
        )
        uow.commit()
        stored = uow.embeddings.get(
            workspace_id,
            owner_kind="claim",
            owner_id=owner_id,
            provider="openai",
            model_tag="text-embedding-3-small",
            text_sha256="a" * 64,
        )
        assert stored is not None
        assert len(stored) == 1536
        assert stored[-1] == pytest.approx(1.0)


def test_changing_index_provider_re_embeds(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = _uow_factory(session_factory)
    embedder = _CountingEmbedding()
    worker = SqlAnalysisWorker(uow_factory, embedding_port=embedder)
    client = _sql_client(session_factory, worker=worker)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    assert created.status_code == 202
    first = worker.process_next()
    assert first is not None
    assert first.state is JobState.SUCCEEDED
    assert len(embedder.calls) == 1

    workspace_id = client.cookies["workspace"]
    with uow_factory() as uow:
        uow.provider_settings.put(
            workspace_id,
            ProviderChoice(
                answer_provider_id="hermetic",
                answer_model="rules-v1",
                index_provider_id="openai",
                index_model="text-embedding-3-small",
            ),
        )
        uow.commit()

    role_id = created.json()["role"]["id"]
    reanalysed = client.post(f"/api/roles/{role_id}/reanalyse")
    assert reanalysed.status_code == 202
    second = worker.process_next()
    assert second is not None
    assert second.state is JobState.SUCCEEDED
    assert len(embedder.calls) == 2


def test_deleting_cv_leaves_zero_embeddings(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = _uow_factory(session_factory)
    worker = SqlAnalysisWorker(uow_factory)
    client = _sql_client(session_factory, worker=worker)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    assert created.status_code == 202
    worker.drain()
    workspace_id = client.cookies["workspace"]
    with uow_factory() as uow:
        assert uow.embeddings.list_for_workspace(workspace_id)

    deleted = client.delete("/api/cv")
    assert deleted.status_code == 204
    with uow_factory() as uow:
        assert uow.embeddings.list_for_workspace(workspace_id) == ()


def test_closed_egress_for_index_provider_does_not_fail_analysis(
    session_factory: sessionmaker[Session],
) -> None:
    uow_factory = _uow_factory(session_factory)
    transport = ScriptedTransport({})
    settings = ProviderSettings(
        completion_provider="hermetic",
        embedding_provider="hermetic",
        allow_hosted_providers=False,
        openai_api_key=SecretStr("sk-test-must-not-travel"),
        openai_embedding_model="text-embedding-3-small",
    )
    worker = SqlAnalysisWorker(uow_factory, providers=settings, transport=transport)
    client = _sql_client(session_factory, worker=worker, providers=settings)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    workspace_id = client.cookies["workspace"]
    with uow_factory() as uow:
        uow.provider_settings.put(
            workspace_id,
            ProviderChoice(
                answer_provider_id="hermetic",
                answer_model="rules-v1",
                index_provider_id="openai",
                index_model="text-embedding-3-small",
            ),
        )
        uow.commit()
    created = client.post(
        "/api/roles",
        json={"title": "AE", "company": "Acme", "description": _JD},
    )
    assert created.status_code == 202
    done = worker.process_next()
    assert done is not None
    assert done.state is JobState.SUCCEEDED
    assert transport.calls == []
    role = client.get(f"/api/roles/{created.json()['role']['id']}")
    assert role.status_code == 200
    assert role.json()["status"] == "ready"
