"""Phase 8 — PostgreSQL-backed analysis jobs and transactional publish."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from tests.integration.conftest import make_document

from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.domain.assessment import PROMPT_VERSION
from career_assistant.domain.attribution import RUBRIC_VERSION, AnalysisAttribution
from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.jobs import (
    JobError,
    JobKind,
    JobStage,
    JobState,
    RoleStatus,
    mark_failed,
    mark_running,
    mark_stage,
    mark_succeeded,
    new_role_analysis_job,
)
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoreComponent, ScoreExplanation

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


def test_publish_analysis_is_visible_only_after_commit(uow: SqlUnitOfWork) -> None:
    workspace_id, role_id, _, cv_id, jd_span_id, cv_span_id = _seed_workspace_with_role(
        uow
    )
    job_id = str(uuid.uuid4())
    req = Requirement(
        id=str(uuid.uuid4()),
        text="Production dbt experience",
        competency="dbt",
        seniority_signal=None,
        must_have=True,
        source_span_id=jd_span_id,
        extraction_confidence=0.9,
        is_vague=False,
    )
    claim = Claim(
        id=str(uuid.uuid4()),
        competency="dbt",
        context="Owned dbt models in production.",
        duration_signal="2y",
        recency_signal="recent",
        source_span_ids=(cv_span_id,),
        extraction_confidence=0.9,
    )
    mapping = RequirementMapping(
        requirement_id=req.id,
        status=MappingStatus.MET,
        reason_code=MappingReason.MATCHED,
        justifying_span_ids=claim.source_span_ids,
        justifying_claim_ids=(claim.id,),
    )
    explanation = ScoreExplanation(
        score=100.0,
        band="strong",
        components=(
            ScoreComponent(
                requirement_id=req.id,
                must_have=True,
                status=MappingStatus.MET,
                weight=3.0,
                status_factor=1.0,
                recency_factor=1.0,
                contribution=3.0,
            ),
        ),
        denominator=3.0,
        numerator=3.0,
    )

    terminal = mark_succeeded(
        mark_stage(
            mark_running(
                new_role_analysis_job(
                    job_id=job_id,
                    workspace_id=workspace_id,
                    role_id=role_id,
                    created_at=NOW,
                ),
                at=NOW,
            ),
            JobStage.SCORING,
        ),
        at=NOW + timedelta(seconds=5),
    )

    with uow:
        uow.jobs.enqueue(
            new_role_analysis_job(
                job_id=job_id,
                workspace_id=workspace_id,
                role_id=role_id,
                created_at=NOW,
            )
        )
        uow.analysis.publish(
            workspace_id=workspace_id,
            role_id=role_id,
            analysis_version=1,
            cv_document_id=cv_id,
            requirements=(req,),
            claims=(claim,),
            mappings=(mapping,),
            explanation=explanation,
            job=terminal,
        )
        other = SqlUnitOfWork(uow._session_factory)  # noqa: SLF001
        with other:
            assert other.analysis.list_mappings(workspace_id, role_id) == ()
        uow.commit()

    with uow:
        assert uow.roles.get(workspace_id, role_id).status is RoleStatus.READY
        assert uow.jobs.get(workspace_id, job_id).state is JobState.SUCCEEDED
        mappings = uow.analysis.list_mappings(workspace_id, role_id)
        assert len(mappings) == 1
        assert mappings[0].status is MappingStatus.MET


def test_reload_keeps_claim_detail_requirement_conditions_and_assessment(
    uow: SqlUnitOfWork,
) -> None:
    """PLAN 13D.5 — a restart reads the saved analysis, including a non-match.

    An introductory course must not come back as meeting production leadership,
    and the stored employer, dates, confidence and seniority must not be replaced.
    """
    workspace_id, role_id, _, cv_id, jd_span_id, cv_span_id = _seed_workspace_with_role(
        uow
    )
    job_id = str(uuid.uuid4())
    requirement = Requirement(
        id=str(uuid.uuid4()),
        text="Five years leading production Python systems",
        competency="python",
        seniority_signal="lead",
        must_have=True,
        source_span_id=jd_span_id,
        extraction_confidence=0.42,
        is_vague=False,
    )
    claim = Claim(
        id=str(uuid.uuid4()),
        competency="python",
        context="Completed an introductory Python course.",
        duration_signal="course",
        recency_signal="recent",
        source_span_ids=(cv_span_id,),
        extraction_confidence=0.42,
        employer="Northwind",
        title="Student",
        scope="one classroom",
        technologies=("Python",),
        outcome="finished the exercises",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 3, 1),
    )
    mapping = RequirementMapping(
        requirement_id=requirement.id,
        status=MappingStatus.MISSING,
        reason_code=MappingReason.ASSESSMENT_INCOMPLETE,
        justifying_span_ids=(),
        justifying_claim_ids=(),
    )
    explanation = ScoreExplanation(
        score=0.0,
        band="limited",
        components=(
            ScoreComponent(
                requirement_id=requirement.id,
                must_have=True,
                status=MappingStatus.MISSING,
                weight=3.0,
                status_factor=0.0,
                recency_factor=1.0,
                contribution=0.0,
            ),
        ),
        denominator=3.0,
        numerator=0.0,
    )
    terminal = mark_succeeded(
        mark_stage(
            mark_running(
                new_role_analysis_job(
                    job_id=job_id,
                    workspace_id=workspace_id,
                    role_id=role_id,
                    created_at=NOW,
                ),
                at=NOW,
            ),
            JobStage.SCORING,
        ),
        at=NOW + timedelta(seconds=2),
    )
    with uow:
        uow.jobs.enqueue(
            new_role_analysis_job(
                job_id=job_id,
                workspace_id=workspace_id,
                role_id=role_id,
                created_at=NOW,
            )
        )
        uow.analysis.publish(
            workspace_id=workspace_id,
            role_id=role_id,
            analysis_version=1,
            cv_document_id=cv_id,
            requirements=(requirement,),
            claims=(claim,),
            mappings=(mapping,),
            explanation=explanation,
            job=terminal,
            attribution=AnalysisAttribution(
                provider="ollama",
                model="llama3.1",
                prompt_version=PROMPT_VERSION,
                rubric_version=RUBRIC_VERSION,
                left_machine=False,
                failure_status="assessment_incomplete",
            ),
        )
        uow.commit()

    def uow_factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(uow._session_factory)  # noqa: SLF001

    role_store = SqlRoleStore(
        cv_store=SqlCvStore(uow_factory),
        uow_factory=uow_factory,
    )
    bundle = role_store.require_analysis(workspace_id, role_id)
    loaded_requirement = bundle.requirements[0]
    loaded_claim = bundle.claims[0]
    assert loaded_requirement.seniority_signal == "lead"
    assert loaded_requirement.extraction_confidence == 0.42
    assert loaded_claim.employer == "Northwind"
    assert loaded_claim.title == "Student"
    assert loaded_claim.scope == "one classroom"
    assert loaded_claim.technologies == ("Python",)
    assert loaded_claim.outcome == "finished the exercises"
    assert loaded_claim.extraction_confidence == 0.42
    assert loaded_claim.period_start == date(2024, 1, 1)
    assert loaded_claim.period_end == date(2024, 3, 1)
    assert bundle.mappings[0].status is MappingStatus.MISSING
    assert bundle.mappings[0].reason_code is MappingReason.ASSESSMENT_INCOMPLETE
    assert bundle.explanation.score == 0.0
    assert bundle.attribution is not None
    assert bundle.attribution.provider == "ollama"
    assert bundle.attribution.model == "llama3.1"
    assert bundle.attribution.prompt_version == PROMPT_VERSION
    assert bundle.attribution.rubric_version == RUBRIC_VERSION
    assert bundle.attribution.left_machine is False
    assert bundle.attribution.failure_status == "assessment_incomplete"


def test_failed_job_discards_partials_and_leaves_role_failed(
    uow: SqlUnitOfWork,
) -> None:
    workspace_id, role_id, _, _, _, _ = _seed_workspace_with_role(uow)
    job_id = str(uuid.uuid4())
    failed = mark_failed(
        mark_stage(
            mark_running(
                new_role_analysis_job(
                    job_id=job_id,
                    workspace_id=workspace_id,
                    role_id=role_id,
                    created_at=NOW,
                ),
                at=NOW,
            ),
            JobStage.EXTRACTING_CLAIMS,
        ),
        at=NOW + timedelta(seconds=1),
        error=JobError(
            code="extracting_claims_failed",
            message="Analysis failed during this stage.",
        ),
    )
    with uow:
        uow.jobs.enqueue(
            new_role_analysis_job(
                job_id=job_id,
                workspace_id=workspace_id,
                role_id=role_id,
                created_at=NOW,
            )
        )
        uow.analysis.fail_job(
            workspace_id=workspace_id,
            role_id=role_id,
            job=failed,
        )
        uow.commit()

    with uow:
        assert uow.roles.get(workspace_id, role_id).status is RoleStatus.FAILED
        assert uow.jobs.get(workspace_id, job_id).state is JobState.FAILED
        assert uow.analysis.list_mappings(workspace_id, role_id) == ()


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
