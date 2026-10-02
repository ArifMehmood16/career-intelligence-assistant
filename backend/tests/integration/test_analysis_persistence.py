"""Job transaction behavior on the sole chunk/verdict analysis."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.conftest import make_document
from tests.integration.test_v2_analysis_persistence import (
    ATTRIBUTION,
    RUBRIC,
    _NoCache,
    _publish,
    _run,
    _world,
)
from tests.integration.test_v2_analysis_persistence import (
    NOW as ANALYSIS_NOW,
)

from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.adapters.persistence.v2_analysis_repos import V2Publication
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.jobs import (
    JobError,
    JobKind,
    JobState,
    RoleStatus,
    mark_failed,
    mark_running,
    mark_succeeded,
    new_role_analysis_job,
)

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 18, 16, 0, tzinfo=UTC)


def _seed_workspace_with_role(
    uow: SqlUnitOfWork,
) -> tuple[str, str, str, str, str, str]:
    """Return workspace, role, jd_id, cv_id, jd_span_id, cv_span_id."""
    workspace_id = str(uuid.uuid4())
    jd = make_document(
        kind=DocumentKind.JOB_DESCRIPTION,
        text="Must have:\n- Production dbt experience\n",
        is_active=False,
    )
    cv = make_document(kind=DocumentKind.CV, text="Owned dbt models in production.")
    role_id = str(uuid.uuid4())
    with uow:
        uow.workspaces.ensure(workspace_id)
        stored_cv = uow.documents.save_admitted(workspace_id, cv)
        stored_jd = uow.documents.save_admitted(workspace_id, jd)
        role = uow.roles.create(
            workspace_id=workspace_id,
            role_id=role_id,
            title="Analytics Engineer",
            company="Acme",
            job_description_document_id=stored_jd.id,
            status=RoleStatus.ANALYSING,
        )
        uow.commit()
    return (
        workspace_id,
        role.id,
        stored_jd.id,
        stored_cv.id,
        jd.spans[0].id,
        cv.spans[0].id,
    )


def test_enqueue_persists_queued_job_and_analysing_role(uow: SqlUnitOfWork) -> None:
    workspace_id, role_id, _, _, _, _ = _seed_workspace_with_role(uow)
    job = new_role_analysis_job(
        job_id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        role_id=role_id,
        created_at=NOW,
    )
    with uow:
        stored = uow.jobs.enqueue(job)
        uow.commit()

    with uow:
        fetched = uow.jobs.get(workspace_id, stored.id)
        assert fetched is not None
        assert fetched.state is JobState.QUEUED
        assert fetched.kind is JobKind.ROLE_ANALYSIS
        assert fetched.stage is None
        role = uow.roles.get(workspace_id, role_id)
        assert role is not None
        assert role.status is RoleStatus.ANALYSING


def test_current_publication_is_visible_only_after_commit(
    uow: SqlUnitOfWork, session_factory: sessionmaker[Session]
) -> None:
    world = _world(uow)
    analysis = _run(session_factory, world, _NoCache())
    with uow:
        job = uow.jobs.get(world.workspace, world.job)
        assert job is not None
        uow.v2.publish(
            V2Publication(
                workspace_id=world.workspace,
                role_id=world.role,
                analysis_version=1,
                job=mark_succeeded(mark_running(job, at=ANALYSIS_NOW), at=ANALYSIS_NOW),
                analysis=analysis,
                rubric_version=RUBRIC.version,
                attribution=ATTRIBUTION,
            )
        )
        with SqlUnitOfWork(session_factory) as reader:
            assert reader.v2.result(world.workspace, world.role) is None
        uow.commit()
    with uow:
        result = uow.v2.result(world.workspace, world.role)
        assert result is not None
        assert result.score == analysis.fit.score
        assert uow.jobs.get(world.workspace, world.job).state is JobState.SUCCEEDED


def test_reloaded_views_use_the_published_current_score_and_evidence(
    uow: SqlUnitOfWork, session_factory: sessionmaker[Session]
) -> None:
    world = _world(uow)
    analysis = _run(session_factory, world, _NoCache())
    _publish(uow, world, analysis)

    def factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    store = SqlRoleStore(cv_store=SqlCvStore(factory), uow_factory=factory)
    bundle = store.require_analysis(world.workspace, world.role)
    assert bundle.explanation.score == analysis.fit.score
    assert len(bundle.requirements) == len(analysis.requirements)
    assert {mapping.requirement_id for mapping in bundle.mappings} == {
        requirement.packet.requirement_id for requirement in analysis.requirements
    }
    assert all(
        span.document_id == world.documents.cv.document_id
        for span in bundle.cv_claim_spans
    )
    assert bundle.attribution is not None
    assert bundle.attribution.provider == ATTRIBUTION.provider
    assert bundle.attribution.model == ATTRIBUTION.model


def test_failed_job_leaves_no_publishable_result(uow: SqlUnitOfWork) -> None:
    world = _world(uow)
    with uow:
        job = uow.jobs.get(world.workspace, world.job)
        assert job is not None
        failed = mark_failed(
            mark_running(job, at=NOW),
            at=NOW,
            error=JobError("chunking_incomplete", "Analysis failed."),
        )
        uow.analysis.fail_job(
            workspace_id=world.workspace, role_id=world.role, job=failed
        )
        uow.commit()
    with uow:
        assert uow.roles.get(world.workspace, world.role).status is RoleStatus.FAILED
        assert uow.jobs.get(world.workspace, world.job).state is JobState.FAILED
        assert uow.v2.result(world.workspace, world.role) is None


def test_failed_reanalysis_restores_the_previous_published_current_score(
    uow: SqlUnitOfWork, session_factory: sessionmaker[Session]
) -> None:
    world = _world(uow)
    analysis = _run(session_factory, world, _NoCache())
    _publish(uow, world, analysis)

    def factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    store = SqlRoleStore(cv_store=SqlCvStore(factory), uow_factory=factory)
    _, new_job = store.reanalyse(world.workspace, world.role)
    new_job_id = new_job.id
    with uow:
        job = uow.jobs.get(world.workspace, new_job_id)
        assert job is not None
        failed = mark_failed(
            mark_running(job, at=NOW),
            at=NOW,
            error=JobError("assessment_incomplete", "Incomplete analysis."),
        )
        uow.analysis.fail_job(
            workspace_id=world.workspace, role_id=world.role, job=failed
        )
        uow.commit()
    view = store.get_role(world.workspace, world.role)
    assert view is not None and view.status == "ready"
    assert view.fit_score == round(analysis.fit.score)
    with uow:
        assert uow.roles.get(world.workspace, world.role).analysis_version == 1
        assert uow.jobs.get(world.workspace, new_job_id).state is JobState.FAILED


def test_duplicate_enqueue_returns_existing_active_job(uow: SqlUnitOfWork) -> None:
    workspace_id, role_id, _, _, _, _ = _seed_workspace_with_role(uow)
    first_id = str(uuid.uuid4())
    second_id = str(uuid.uuid4())
    with uow:
        first = uow.jobs.enqueue(
            new_role_analysis_job(
                job_id=first_id,
                workspace_id=workspace_id,
                role_id=role_id,
                created_at=NOW,
            )
        )
        again = uow.jobs.enqueue_idempotent(
            new_role_analysis_job(
                job_id=second_id,
                workspace_id=workspace_id,
                role_id=role_id,
                created_at=NOW,
            )
        )
        uow.commit()
    assert again.id == first.id


def test_cv_replace_enqueues_reanalysis_in_same_transaction(
    uow: SqlUnitOfWork,
) -> None:
    workspace_id, role_id, _, _, _, _ = _seed_workspace_with_role(uow)
    new_cv = make_document(
        kind=DocumentKind.CV, text="Rewrote the CV with more dbt evidence."
    )
    reanalysis_job_id = str(uuid.uuid4())
    with uow:
        uow.documents.replace_cv(workspace_id, new_cv)
        job_ids = uow.jobs.enqueue_reanalysis_for_workspace(
            workspace_id=workspace_id,
            job_ids=(reanalysis_job_id,),
            created_at=NOW,
        )
        uow.commit()

    assert job_ids == (reanalysis_job_id,)
    with uow:
        role = uow.roles.get(workspace_id, role_id)
        assert role is not None
        assert role.status is RoleStatus.ANALYSING
        job = uow.jobs.get(workspace_id, reanalysis_job_id)
        assert job is not None
        assert job.state is JobState.QUEUED
