"""Phase 8 — role analysis enqueue, worker pipeline and publish (unit, fakes).

These specs lock orchestration behaviour before persistence/worker code exists.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from career_assistant.application.analysis.service import (
    AnalysisDocuments,
    AnalysisService,
    JobClock,
)
from career_assistant.application.ports.adjudication import (
    AdjudicationPair,
    AdjudicationPort,
    AssessmentItem,
)
from career_assistant.application.ports.embedding import (
    EmbeddingCachePort,
    EmbeddingPort,
)
from career_assistant.application.ports.extraction import (
    ClaimExtractionPort,
    ClaimExtractionResult,
    RequirementExtractionPort,
    RequirementExtractionResult,
)
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric
from career_assistant.domain.assessment import EvidenceAssessment
from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.jobs import JobStage, JobState, RoleStatus
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoringRubric

ROOT = Path(__file__).resolve().parents[3]
RUBRIC = load_scoring_rubric(ROOT / "config" / "scoring_rubric.toml")
NOW = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)


@dataclass
class _FixedClock:
    now: datetime

    def __call__(self) -> datetime:
        return self.now


@dataclass
class _MemDocs:
    jd_text: str
    cv_text: str
    jd_id: str = "jd-1"
    cv_id: str = "cv-1"

    def job_description_text(self, workspace_id: str, role_id: str) -> tuple[str, str]:
        return self.jd_id, self.jd_text

    def active_cv_text(self, workspace_id: str) -> tuple[str, str]:
        return self.cv_id, self.cv_text


@dataclass
class _MemPublisher:
    published: list[dict[str, object]] = field(default_factory=list)
    discarded: list[str] = field(default_factory=list)

    def publish(
        self,
        *,
        workspace_id: str,
        role_id: str,
        analysis_version: int,
        requirements: tuple[Requirement, ...],
        claims: tuple[Claim, ...],
        mappings: object,
        explanation: object,
    ) -> None:
        self.published.append(
            {
                "workspace_id": workspace_id,
                "role_id": role_id,
                "analysis_version": analysis_version,
                "requirements": requirements,
                "claims": claims,
                "mappings": mappings,
                "explanation": explanation,
            }
        )

    def discard_partial(self, *, workspace_id: str, role_id: str) -> None:
        self.discarded.append(f"{workspace_id}:{role_id}")

    def has_published_mappings(self, role_id: str) -> bool:
        return any(p["role_id"] == role_id for p in self.published)


class _OkRequirements:
    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> RequirementExtractionResult:
        assert document_kind is DocumentKind.JOB_DESCRIPTION
        req = Requirement(
            id="req-dbt",
            text="Production dbt experience",
            competency="dbt",
            seniority_signal=None,
            must_have=True,
            source_span_id="span-req",
            extraction_confidence=0.9,
            is_vague=False,
        )
        return RequirementExtractionResult(requirements=(req,), spans=())


class _OkClaims:
    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> ClaimExtractionResult:
        assert document_kind is DocumentKind.CV
        claim = Claim(
            id="claim-dbt",
            competency="dbt",
            context="Owned dbt models in production.",
            duration_signal="2y",
            recency_signal="recent",
            source_span_ids=("span-claim",),
            extraction_confidence=0.9,
        )
        return ClaimExtractionResult(claims=(claim,), spans=())


class _FailClaims:
    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> ClaimExtractionResult:
        raise RuntimeError("claim extractor exploded")


class _SilentAssessor:
    """Returns no assessments, so every retrieved requirement stays incomplete."""

    @property
    def decides_support(self) -> bool:
        return True

    def assess(
        self, items: tuple[AssessmentItem, ...] | list[AssessmentItem]
    ) -> dict[str, EvidenceAssessment]:
        return {}

    def adjudicate(
        self, pairs: tuple[AdjudicationPair, ...] | list[AdjudicationPair]
    ) -> dict[tuple[str, str], bool]:
        return {}


def _service(
    *,
    claims: ClaimExtractionPort | None = None,
    requirements: RequirementExtractionPort | None = None,
    publisher: _MemPublisher | None = None,
    adjudicator: AdjudicationPort | None = None,
    clock: JobClock | None = None,
    docs: AnalysisDocuments | None = None,
    rubric: ScoringRubric | None = None,
    embedding: EmbeddingPort | None = None,
    embedding_cache: EmbeddingCachePort | None = None,
    embedding_provider_id: str = "hermetic",
    embedding_model_tag: str = "lexical-hash-v1",
) -> tuple[AnalysisService, _MemPublisher]:
    pub = publisher or _MemPublisher()
    service = AnalysisService(
        documents=docs
        or _MemDocs(
            jd_text="Must have:\n- Production dbt experience\n",
            cv_text="Owned dbt models in production.",
        ),
        requirement_extractor=requirements or _OkRequirements(),
        claim_extractor=claims or _OkClaims(),
        publisher=pub,
        rubric=rubric or RUBRIC,
        clock=clock or _FixedClock(NOW),
        running_timeout=timedelta(minutes=10),
        max_concurrent=2,
        embedding=embedding,
        embedding_cache=embedding_cache,
        embedding_provider_id=embedding_provider_id,
        embedding_model_tag=embedding_model_tag,
        adjudicator=adjudicator,
    )
    return service, pub


def test_incomplete_assessment_fails_the_job_and_publishes_no_score() -> None:
    """PLAN 13D.6a — a missing assessment is a failed job, not a fit score."""
    service, pub = _service(adjudicator=_SilentAssessor())
    service.create_role(
        workspace_id="ws-1",
        role_id="role-1",
        title="AE",
        job_id="job-1",
    )
    done = service.process_next()
    assert done is not None
    assert done.state is JobState.FAILED
    assert done.error is not None
    assert done.error.code == "assessment_incomplete"
    assert service.get_role("ws-1", "role-1").status is RoleStatus.FAILED
    assert pub.published == []


class _PartialRequirements(_OkRequirements):
    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> RequirementExtractionResult:
        result = super().extract(
            document_id=document_id,
            document_kind=document_kind,
            normalised_text=normalised_text,
        )
        return RequirementExtractionResult(
            requirements=result.requirements,
            spans=result.spans,
            complete=False,
        )


class _PartialClaims:
    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> ClaimExtractionResult:
        assert document_kind is DocumentKind.CV
        return ClaimExtractionResult(claims=(), spans=(), complete=False)


def test_incomplete_claim_extraction_does_not_replace_a_valid_claim_set() -> None:
    """PLAN 13D.6d — a failed CV extraction leaves the previous claims in place."""
    publisher = _MemPublisher()
    publisher.published.append({"role_id": "role-1", "claims": ("previous",)})
    service, pub = _service(claims=_PartialClaims(), publisher=publisher)
    service.create_role(
        workspace_id="ws-1",
        role_id="role-1",
        title="AE",
        job_id="job-1",
    )
    done = service.process_next()
    assert done is not None
    assert done.state is JobState.FAILED
    assert done.error is not None
    assert done.error.code == "extraction_incomplete"
    assert pub.published == [{"role_id": "role-1", "claims": ("previous",)}]


def test_incomplete_extraction_fails_the_job_and_publishes_no_score() -> None:
    """PLAN 13D.6c — a partial extraction is not a fit score."""
    service, pub = _service(requirements=_PartialRequirements())
    service.create_role(
        workspace_id="ws-1",
        role_id="role-1",
        title="AE",
        job_id="job-1",
    )
    done = service.process_next()
    assert done is not None
    assert done.state is JobState.FAILED
    assert done.error is not None
    assert done.error.code == "extraction_incomplete"
    assert service.get_role("ws-1", "role-1").status is RoleStatus.FAILED
    assert pub.published == []


def test_create_role_returns_immediately_with_queued_job_and_analysing_status() -> None:
    service, _ = _service()
    role, job = service.create_role(
        workspace_id="ws-1",
        role_id="role-1",
        title="Analytics Engineer",
        job_id="job-1",
    )
    assert role.status is RoleStatus.ANALYSING
    assert job.state is JobState.QUEUED
    assert job.id == "job-1"
    assert job.role_id == "role-1"
    assert service.get_job("job-1").state is JobState.QUEUED


def test_worker_runs_pipeline_stages_and_publishes_ready_role() -> None:
    service, pub = _service()
    service.create_role(
        workspace_id="ws-1",
        role_id="role-1",
        title="AE",
        job_id="job-1",
    )
    done = service.process_next()
    assert done is not None
    assert done.state is JobState.SUCCEEDED
    assert done.stage is JobStage.SCORING
    role = service.get_role("ws-1", "role-1")
    assert role.status is RoleStatus.READY
    assert pub.has_published_mappings("role-1")
    assert len(pub.published) == 1
    explanation = pub.published[0]["explanation"]
    assert explanation.score >= 0  # type: ignore[union-attr]


def test_forced_failure_sets_failed_role_and_discards_partial_results(
    caplog: logging.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="career_assistant")
    service, pub = _service(claims=_FailClaims())
    service.create_role(
        workspace_id="ws-1",
        role_id="role-1",
        title="AE",
        job_id="job-1",
    )
    done = service.process_next()
    assert done is not None
    assert done.state is JobState.FAILED
    assert done.stage is JobStage.EXTRACTING_CLAIMS
    assert done.error is not None
    assert done.error.code == "extracting_claims_failed"
    role = service.get_role("ws-1", "role-1")
    assert role.status is RoleStatus.FAILED
    assert not pub.has_published_mappings("role-1")
    assert pub.discarded == ["ws-1:role-1"]
    assert "worker.failed" in caplog.text
    assert "error_type=RuntimeError" in caplog.text


def test_duplicate_enqueue_does_not_double_run() -> None:
    service, pub = _service()
    service.create_role(
        workspace_id="ws-1",
        role_id="role-1",
        title="AE",
        job_id="job-1",
    )
    again = service.enqueue_reanalysis(
        workspace_id="ws-1",
        role_id="role-1",
        job_id="job-2",
    )
    assert again.id == "job-1"
    service.process_next()
    service.process_next()
    assert len(pub.published) == 1


def test_startup_recovers_stale_running_and_keeps_queued_eligible() -> None:
    clock = _FixedClock(NOW)
    service, _ = _service(clock=clock)
    service.create_role(
        workspace_id="ws-1",
        role_id="role-1",
        title="AE",
        job_id="job-stale",
    )
    service.mark_job_running_for_tests(
        "job-stale",
        started_at=NOW - timedelta(minutes=30),
    )
    service.create_role(
        workspace_id="ws-1",
        role_id="role-2",
        title="DE",
        job_id="job-queued",
    )
    service.startup()
    stale = service.get_job("job-stale")
    assert stale.state is JobState.FAILED
    assert stale.error is not None
    assert stale.error.code == "stale_running"
    assert service.get_role("ws-1", "role-1").status is RoleStatus.FAILED
    assert service.get_job("job-queued").state is JobState.QUEUED


def test_cv_replace_enqueues_reanalysis_for_every_role() -> None:
    service, _ = _service()
    service.create_role(
        workspace_id="ws-1", role_id="role-a", title="A", job_id="job-a"
    )
    service.create_role(
        workspace_id="ws-1", role_id="role-b", title="B", job_id="job-b"
    )
    service.process_next()
    service.process_next()
    job_ids = service.enqueue_reanalysis_after_cv_replace(
        workspace_id="ws-1",
        new_job_ids=("job-a2", "job-b2"),
    )
    assert set(job_ids) == {"job-a2", "job-b2"}
    assert service.get_role("ws-1", "role-a").status is RoleStatus.ANALYSING
    assert service.get_role("ws-1", "role-b").status is RoleStatus.ANALYSING


def test_identical_inputs_produce_identical_published_score() -> None:
    service_a, pub_a = _service()
    service_b, pub_b = _service()
    service_a.create_role(
        workspace_id="ws-1", role_id="role-1", title="AE", job_id="job-1"
    )
    service_b.create_role(
        workspace_id="ws-1", role_id="role-1", title="AE", job_id="job-1"
    )
    service_a.process_next()
    service_b.process_next()
    score_a = pub_a.published[0]["explanation"].score  # type: ignore[union-attr]
    score_b = pub_b.published[0]["explanation"].score  # type: ignore[union-attr]
    assert score_a == score_b


def test_bounded_dispatcher_respects_max_concurrent() -> None:
    service, _ = _service()
    service.create_role(workspace_id="ws-1", role_id="r1", title="A", job_id="j1")
    service.create_role(workspace_id="ws-1", role_id="r2", title="B", job_id="j2")
    service.create_role(workspace_id="ws-1", role_id="r3", title="C", job_id="j3")
    started = service.start_available(limit=10)
    assert len(started) == 2
    assert service.get_job("j3").state is JobState.QUEUED
