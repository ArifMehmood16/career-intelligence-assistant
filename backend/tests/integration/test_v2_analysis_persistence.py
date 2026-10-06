"""PLAN 18.10 — a v2 analysis is published, read back and reused from PostgreSQL."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.conftest import make_document

from career_assistant.adapters.persistence.index_store import SqlDocumentIndexStore
from career_assistant.adapters.persistence.search_repos import SqlHybridSearch
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.adapters.persistence.v2_analysis_repos import (
    SqlVerdictCache,
    V2Publication,
)
from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.application.analysis.v2 import (
    RoleAnalysisV2,
    V2Analysis,
    V2Documents,
    V2Limits,
)
from career_assistant.application.chunking.service import (
    ChunkingRequest,
    DocumentChunker,
)
from career_assistant.application.indexing.service import DocumentIndexer
from career_assistant.application.judge.cache import ModelIdentity
from career_assistant.application.judge.prompt import JudgeLimits
from career_assistant.application.judge.service import RequirementJudge
from career_assistant.application.ports.verdicts import VerdictCache
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric_v2
from career_assistant.domain.attribution import AnalysisAttribution
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.jobs import (
    RoleStatus,
    mark_running,
    mark_succeeded,
    new_role_analysis_job,
)

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "sample-data" / "fixtures"
RUBRIC = load_scoring_rubric_v2(ROOT / "config" / "scoring_rubric.toml")
AS_OF = date(2026, 9, 1)
NOW = datetime(2026, 9, 1, tzinfo=UTC)
ATTRIBUTION = AnalysisAttribution(
    provider="hermetic",
    model="rules-v1",
    prompt_version="judge-prompt-v1",
    rubric_version=RUBRIC.version,
    left_machine=False,
    failure_status=None,
)


@dataclass(frozen=True)
class World:
    workspace: str
    role: str
    job: str
    documents: V2Documents


def _world(uow: SqlUnitOfWork) -> World:
    cv_text = (FIXTURES / "resumes" / "cv-strong-match.txt").read_text("utf-8")
    jd_text = (FIXTURES / "job-descriptions" / "jd-clean-match.txt").read_text("utf-8")
    ws, role_id = str(uuid.uuid4()), str(uuid.uuid4())
    with uow:
        uow.workspaces.ensure(ws)
        cv = uow.documents.save_admitted(ws, make_document(text=cv_text))
        jd = uow.documents.save_admitted(
            ws,
            make_document(
                kind=DocumentKind.JOB_DESCRIPTION, text=jd_text, is_active=False
            ),
        )
        uow.roles.create(
            workspace_id=ws,
            role_id=role_id,
            title="Data Engineer",
            company="Northwind",
            job_description_document_id=jd.id,
            status=RoleStatus.ANALYSING,
        )
        job = uow.jobs.enqueue(
            new_role_analysis_job(
                job_id=str(uuid.uuid4()),
                workspace_id=ws,
                role_id=role_id,
                created_at=NOW,
            )
        )
        uow.commit()
    return World(
        workspace=ws,
        role=role_id,
        job=job.id,
        documents=V2Documents(
            workspace_id=ws,
            cv=ChunkingRequest(document_id=cv.id, kind=DocumentKind.CV, text=cv_text),
            advert=ChunkingRequest(
                document_id=jd.id, kind=DocumentKind.JOB_DESCRIPTION, text=jd_text
            ),
            as_of=AS_OF,
        ),
    )


def _run(
    session_factory: sessionmaker[Session], world: World, cache: VerdictCache
) -> V2Analysis:
    structured = HermeticStructuredCompleter()
    embedding = HermeticEmbeddingAdapter()
    analysis = RoleAnalysisV2(
        indexer=DocumentIndexer(
            chunker=DocumentChunker(structured),
            embedding=embedding,
            store=SqlDocumentIndexStore(lambda: SqlUnitOfWork(session_factory)),
            max_chars_per_text=8_000,
        ),
        judge=RequirementJudge(
            structured, cache, ModelIdentity("hermetic", "rules-v1"), JudgeLimits()
        ),
        embedding=embedding,
        search=SqlHybridSearch(session_factory),
        rubric=RUBRIC,
        limits=V2Limits(max_rewrites=5, max_chars_per_text=8_000),
    )
    return analysis.run(world.documents)


def _publish(uow: SqlUnitOfWork, world: World, analysis: V2Analysis) -> None:
    with uow:
        job = uow.jobs.get(world.workspace, world.job)
        assert job is not None
        done = mark_succeeded(mark_running(job, at=NOW), at=NOW)
        uow.v2.publish(
            V2Publication(
                workspace_id=world.workspace,
                role_id=world.role,
                analysis_version=1,
                job=done,
                analysis=analysis,
                rubric_version=RUBRIC.version,
                attribution=ATTRIBUTION,
            )
        )
        uow.commit()


class _NoCache:
    def find(self, key: str) -> None:
        return None

    def keep(self, key: str, record: object) -> None:
        return None


def test_a_published_analysis_reads_back_with_its_evidence(
    uow: SqlUnitOfWork, session_factory: sessionmaker[Session]
) -> None:
    world = _world(uow)
    analysis = _run(session_factory, world, _NoCache())
    assert analysis.fit.publishable

    _publish(uow, world, analysis)
    with uow:
        result = uow.v2.result(world.workspace, world.role)
        role = uow.roles.get(world.workspace, world.role)

    assert result is not None and role is not None
    assert role.status is RoleStatus.READY
    assert result.analysis_id == world.job
    assert (result.score, result.band) == (analysis.fit.score, analysis.fit.band)
    assert result.rubric_version == RUBRIC.version
    assert result.coverage == analysis.coverage
    assert result.gaps == analysis.gaps
    assert result.score_components == analysis.fit.components
    assert any(r.packet.experience_expected for r in analysis.requirements)
    for requirement in analysis.requirements:
        stored = next(
            v
            for v in result.verdicts
            if v.requirement_id == requirement.packet.requirement_id
        )
        assert stored.experience_expected == requirement.packet.experience_expected
        assert stored.years_expected == requirement.packet.years_expected
        assert stored.seniority_expected == requirement.packet.seniority_expected
    published = {v.requirement_id: v for v in result.verdicts}
    assert set(published) == set(analysis.match.verdicts)
    for requirement_id, record in analysis.match.verdicts.items():
        stored = published[requirement_id]
        assert stored.verdict == record.verdict
        assert [e.quote for e in stored.evidence] == [
            q.quote for q in record.verdict.evidence
        ]
        assert {e.document_id for e in stored.evidence} <= {
            world.documents.cv.document_id
        }


def test_each_verdict_keeps_its_retrieval_trace(
    uow: SqlUnitOfWork, session_factory: sessionmaker[Session]
) -> None:
    world = _world(uow)
    analysis = _run(session_factory, world, _NoCache())
    _publish(uow, world, analysis)

    requirement_id = next(iter(analysis.match.verdicts))
    with uow:
        traces = uow.v2.traces(world.workspace, world.role, requirement_id)
        missing = uow.v2.traces(world.workspace, world.role, str(uuid.uuid4()))

    assert traces is not None
    expected = analysis.match.traces[requirement_id]
    assert [(t.round, t.query_text) for t in traces] == [
        (r.round, r.query_text) for r in expected if r.hits
    ]
    assert missing is None


def test_a_second_run_reuses_the_published_verdicts(
    uow: SqlUnitOfWork, session_factory: sessionmaker[Session]
) -> None:
    world = _world(uow)
    first = _run(session_factory, world, _NoCache())
    _publish(uow, world, first)

    cache = SqlVerdictCache(lambda: SqlUnitOfWork(session_factory), world.workspace)
    second = _run(session_factory, world, cache)

    assert second.match.verdicts
    assert all(record.cached for record in second.match.verdicts.values())
    assert {k: r.verdict for k, r in second.match.verdicts.items()} == {
        k: r.verdict for k, r in first.match.verdicts.items()
    }
