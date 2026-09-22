"""In-process role analysis orchestration — stages, publish, failure discard."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from career_assistant.application.analysis.relatedness import (
    NullAdjudicator,
    map_role_requirements,
)
from career_assistant.application.analysis.similarity import (
    requirement_claim_similarities,
)
from career_assistant.application.ports.adjudication import AdjudicationPort
from career_assistant.application.ports.embedding import (
    EmbeddingCachePort,
    EmbeddingPort,
)
from career_assistant.application.ports.extraction import (
    ClaimExtractionPort,
    RequirementExtractionPort,
)
from career_assistant.application.scoring.rubric_loader import load_mapping_config
from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.jobs import (
    AnalysisJob,
    JobError,
    JobStage,
    JobState,
    RoleStatus,
    mark_failed,
    mark_running,
    mark_stage,
    mark_succeeded,
    new_role_analysis_job,
    recover_stale_running,
)
from career_assistant.domain.mapping import RequirementMapping
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoreExplanation, ScoringRubric, score_fit
from career_assistant.logconfig import log_event

JobClock = Callable[[], datetime]
_log = logging.getLogger(__name__)
_MAPPING = load_mapping_config(
    Path(__file__).resolve().parents[5] / "config" / "scoring_rubric.toml"
)


@dataclass(frozen=True, slots=True)
class AnalysisRole:
    id: str
    workspace_id: str
    title: str
    status: RoleStatus
    analysis_version: int


@dataclass(frozen=True, slots=True)
class StartupRecovery:
    failed_job_ids: tuple[str, ...]
    dispatched_job_ids: tuple[str, ...]


class AnalysisDocuments(Protocol):
    def job_description_text(
        self, workspace_id: str, role_id: str
    ) -> tuple[str, str]: ...

    def active_cv_text(self, workspace_id: str) -> tuple[str, str]: ...


class AnalysisPublisher(Protocol):
    def publish(
        self,
        *,
        workspace_id: str,
        role_id: str,
        analysis_version: int,
        requirements: tuple[Requirement, ...],
        claims: tuple[Claim, ...],
        mappings: tuple[RequirementMapping, ...],
        explanation: ScoreExplanation,
    ) -> None: ...

    def discard_partial(self, *, workspace_id: str, role_id: str) -> None: ...


class AnalysisService:
    """Bounded in-process analysis worker with injectable document/publisher ports."""

    def __init__(
        self,
        *,
        documents: AnalysisDocuments,
        requirement_extractor: RequirementExtractionPort,
        claim_extractor: ClaimExtractionPort,
        publisher: AnalysisPublisher,
        rubric: ScoringRubric,
        clock: JobClock,
        running_timeout: timedelta,
        max_concurrent: int,
        embedding: EmbeddingPort | None = None,
        embedding_cache: EmbeddingCachePort | None = None,
        embedding_provider_id: str = "hermetic",
        embedding_model_tag: str = "lexical-hash-v1",
        adjudicator: AdjudicationPort | None = None,
        similarity_floor: float | None = None,
    ) -> None:
        self._documents = documents
        self._requirement_extractor = requirement_extractor
        self._claim_extractor = claim_extractor
        self._publisher = publisher
        self._rubric = rubric
        self._clock = clock
        self._running_timeout = running_timeout
        self._max_concurrent = max_concurrent
        self._embedding = embedding
        self._embedding_cache = embedding_cache
        self._embedding_provider_id = embedding_provider_id
        self._embedding_model_tag = embedding_model_tag
        self._adjudicator = adjudicator or NullAdjudicator()
        self._similarity_floor = (
            similarity_floor
            if similarity_floor is not None
            else _MAPPING.similarity_floor
        )
        self._roles: dict[str, AnalysisRole] = {}
        self._jobs: dict[str, AnalysisJob] = {}
        self._role_order: list[str] = []

    def create_role(
        self,
        *,
        workspace_id: str,
        role_id: str,
        title: str,
        job_id: str,
    ) -> tuple[AnalysisRole, AnalysisJob]:
        role = AnalysisRole(
            id=role_id,
            workspace_id=workspace_id,
            title=title,
            status=RoleStatus.ANALYSING,
            analysis_version=1,
        )
        self._roles[role_id] = role
        if role_id not in self._role_order:
            self._role_order.append(role_id)
        job = new_role_analysis_job(
            job_id=job_id,
            workspace_id=workspace_id,
            role_id=role_id,
            created_at=self._clock(),
        )
        self._jobs[job_id] = job
        return role, job

    def get_role(self, workspace_id: str, role_id: str) -> AnalysisRole:
        role = self._roles[role_id]
        if role.workspace_id != workspace_id:
            raise KeyError(role_id)
        return role

    def get_job(self, job_id: str) -> AnalysisJob:
        return self._jobs[job_id]

    def enqueue_reanalysis(
        self,
        *,
        workspace_id: str,
        role_id: str,
        job_id: str,
    ) -> AnalysisJob:
        active = self._active_job_for_role(role_id)
        if active is not None:
            return active
        role = self.get_role(workspace_id, role_id)
        self._roles[role_id] = replace(role, status=RoleStatus.ANALYSING)
        job = new_role_analysis_job(
            job_id=job_id,
            workspace_id=workspace_id,
            role_id=role_id,
            created_at=self._clock(),
        )
        self._jobs[job_id] = job
        return job

    def enqueue_reanalysis_after_cv_replace(
        self,
        *,
        workspace_id: str,
        new_job_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        roles = [
            self._roles[rid]
            for rid in self._role_order
            if self._roles[rid].workspace_id == workspace_id
        ]
        if len(new_job_ids) != len(roles):
            raise ValueError("new_job_ids must match workspace role count")
        assigned: list[str] = []
        for role, job_id in zip(roles, new_job_ids, strict=True):
            # Force a fresh job even if a prior analysis succeeded.
            self._roles[role.id] = replace(role, status=RoleStatus.ANALYSING)
            # Drop terminal jobs from the active check by creating a new id always.
            for existing in list(self._jobs.values()):
                if existing.role_id == role.id and existing.state in {
                    JobState.QUEUED,
                    JobState.RUNNING,
                }:
                    # Cancel in-flight by failing it so the new job can run.
                    self._jobs[existing.id] = mark_failed(
                        existing
                        if existing.state is JobState.RUNNING
                        else mark_running(existing, at=self._clock()),
                        at=self._clock(),
                        error=JobError(
                            code="superseded",
                            message="Superseded by CV replacement re-analysis.",
                        ),
                    )
            job = new_role_analysis_job(
                job_id=job_id,
                workspace_id=workspace_id,
                role_id=role.id,
                created_at=self._clock(),
            )
            self._jobs[job_id] = job
            assigned.append(job_id)
        return tuple(assigned)

    def mark_job_running_for_tests(
        self, job_id: str, *, started_at: datetime
    ) -> AnalysisJob:
        job = self._jobs[job_id]
        if job.state is JobState.QUEUED:
            job = mark_running(job, at=started_at)
        elif job.state is JobState.RUNNING:
            job = replace(job, started_at=started_at)
        else:
            raise ValueError(f"cannot mark {job.state} as running for tests")
        self._jobs[job_id] = job
        role = self._roles[job.role_id]
        self._roles[job.role_id] = replace(role, status=RoleStatus.ANALYSING)
        return job

    def startup(self) -> StartupRecovery:
        failed: list[str] = []
        for job_id, job in list(self._jobs.items()):
            if job.state is not JobState.RUNNING:
                continue
            recovered = recover_stale_running(
                job,
                now=self._clock(),
                running_timeout=self._running_timeout,
            )
            if recovered.state is JobState.FAILED:
                self._jobs[job_id] = recovered
                role = self._roles[job.role_id]
                self._roles[job.role_id] = replace(role, status=RoleStatus.FAILED)
                self._publisher.discard_partial(
                    workspace_id=job.workspace_id, role_id=job.role_id
                )
                failed.append(job_id)
        dispatched = tuple(
            j.id for j in self._jobs.values() if j.state is JobState.QUEUED
        )
        return StartupRecovery(
            failed_job_ids=tuple(failed),
            dispatched_job_ids=dispatched,
        )

    def start_available(self, *, limit: int) -> tuple[AnalysisJob, ...]:
        started: list[AnalysisJob] = []
        running_count = sum(
            1 for j in self._jobs.values() if j.state is JobState.RUNNING
        )
        for job in self._jobs.values():
            if len(started) >= limit:
                break
            if running_count >= self._max_concurrent:
                break
            if job.state is not JobState.QUEUED:
                continue
            running = mark_running(job, at=self._clock())
            self._jobs[job.id] = running
            started.append(running)
            running_count += 1
            log_event(
                _log,
                "worker.claimed",
                job_id=running.id,
                role_id=running.role_id,
            )
        return tuple(started)

    def process_next(self) -> AnalysisJob | None:
        job = next(
            (j for j in self._jobs.values() if j.state is JobState.QUEUED),
            None,
        )
        if job is None:
            return None
        return self._run_job(job.id)

    def _active_job_for_role(self, role_id: str) -> AnalysisJob | None:
        for job in self._jobs.values():
            if job.role_id == role_id and job.state in {
                JobState.QUEUED,
                JobState.RUNNING,
            }:
                return job
        return None

    def _run_job(self, job_id: str) -> AnalysisJob:
        job = mark_running(self._jobs[job_id], at=self._clock())
        self._jobs[job_id] = job
        role = self._roles[job.role_id]
        workspace_id = job.workspace_id
        role_id = job.role_id
        log_event(_log, "worker.claimed", job_id=job_id, role_id=role_id)

        try:
            job = mark_stage(job, JobStage.PARSING)
            self._jobs[job_id] = job
            log_event(
                _log,
                "worker.stage",
                job_id=job_id,
                role_id=role_id,
                stage=JobStage.PARSING.value,
            )

            job = mark_stage(job, JobStage.EXTRACTING_REQUIREMENTS)
            self._jobs[job_id] = job
            log_event(
                _log,
                "worker.stage",
                job_id=job_id,
                role_id=role_id,
                stage=JobStage.EXTRACTING_REQUIREMENTS.value,
            )
            jd_id, jd_text = self._documents.job_description_text(workspace_id, role_id)
            req_result = self._requirement_extractor.extract(
                document_id=jd_id,
                document_kind=DocumentKind.JOB_DESCRIPTION,
                normalised_text=jd_text,
            )
            if not req_result.complete:
                failed = mark_failed(
                    job,
                    at=self._clock(),
                    error=JobError(
                        code="extraction_incomplete",
                        message=(
                            "Requirement extraction did not classify every part "
                            "of the job description. This is not a fit score."
                        ),
                    ),
                )
                self._jobs[job_id] = failed
                self._roles[role_id] = replace(role, status=RoleStatus.FAILED)
                log_event(
                    _log,
                    "worker.failed",
                    job_id=job_id,
                    role_id=role_id,
                    stage=JobStage.EXTRACTING_REQUIREMENTS.value,
                    code="extraction_incomplete",
                )
                return failed

            job = mark_stage(job, JobStage.EXTRACTING_CLAIMS)
            self._jobs[job_id] = job
            log_event(
                _log,
                "worker.stage",
                job_id=job_id,
                role_id=role_id,
                stage=JobStage.EXTRACTING_CLAIMS.value,
            )
            cv_id, cv_text = self._documents.active_cv_text(workspace_id)
            claim_result = self._claim_extractor.extract(
                document_id=cv_id,
                document_kind=DocumentKind.CV,
                normalised_text=cv_text,
            )
            if not claim_result.complete:
                failed = mark_failed(
                    job,
                    at=self._clock(),
                    error=JobError(
                        code="extraction_incomplete",
                        message=(
                            "Claim extraction did not classify every part of "
                            "the CV. This is not a fit score."
                        ),
                    ),
                )
                self._jobs[job_id] = failed
                self._roles[role_id] = replace(role, status=RoleStatus.FAILED)
                log_event(
                    _log,
                    "worker.failed",
                    job_id=job_id,
                    role_id=role_id,
                    stage=JobStage.EXTRACTING_CLAIMS.value,
                    code="extraction_incomplete",
                )
                return failed

            job = mark_stage(job, JobStage.MAPPING)
            self._jobs[job_id] = job
            log_event(
                _log,
                "worker.stage",
                job_id=job_id,
                role_id=role_id,
                stage=JobStage.MAPPING.value,
            )
            similarities = requirement_claim_similarities(
                workspace_id=workspace_id,
                requirements=req_result.requirements,
                claims=claim_result.claims,
                embedding=self._embedding,
                cache=self._embedding_cache,
                provider_id=self._embedding_provider_id,
                model_tag=self._embedding_model_tag,
            )
            mappings = map_role_requirements(
                req_result.requirements,
                claim_result.claims,
                similarities=similarities,
                adjudicator=self._adjudicator,
                similarity_floor=self._similarity_floor,
            )

            job = mark_stage(job, JobStage.SCORING)
            self._jobs[job_id] = job
            log_event(
                _log,
                "worker.stage",
                job_id=job_id,
                role_id=role_id,
                stage=JobStage.SCORING.value,
            )
            explanation = score_fit(
                req_result.requirements,
                mappings,
                claim_result.claims,
                self._rubric,
            )
            if explanation.band == "incomplete":
                failed = mark_failed(
                    job,
                    at=self._clock(),
                    error=JobError(
                        code="assessment_incomplete",
                        message=(
                            "Analysis did not assess every scoreable requirement. "
                            "This is not a fit score."
                        ),
                    ),
                )
                self._jobs[job_id] = failed
                self._roles[role_id] = replace(role, status=RoleStatus.FAILED)
                log_event(
                    _log,
                    "worker.failed",
                    job_id=job_id,
                    role_id=role_id,
                    stage=JobStage.SCORING.value,
                    code="assessment_incomplete",
                )
                return failed

            version = role.analysis_version
            self._publisher.publish(
                workspace_id=workspace_id,
                role_id=role_id,
                analysis_version=version,
                requirements=req_result.requirements,
                claims=claim_result.claims,
                mappings=mappings,
                explanation=explanation,
            )
            done = mark_succeeded(job, at=self._clock())
            self._jobs[job_id] = done
            self._roles[role_id] = replace(
                role,
                status=RoleStatus.READY,
                analysis_version=version,
            )
            log_event(
                _log,
                "worker.succeeded",
                job_id=job_id,
                role_id=role_id,
                requirement_count=len(req_result.requirements),
                claim_count=len(claim_result.claims),
                mapping_count=len(mappings),
                similarity_pairs=len(similarities),
            )
            return done
        except Exception as exc:
            stage = job.stage or JobStage.PARSING
            code = f"{stage.value}_failed"
            self._publisher.discard_partial(workspace_id=workspace_id, role_id=role_id)
            running_job = (
                job
                if job.state is JobState.RUNNING
                else mark_running(job, at=self._clock())
            )
            failed = mark_failed(
                running_job,
                at=self._clock(),
                error=JobError(
                    code=code,
                    message="Analysis failed during this stage.",
                ),
            )
            self._jobs[job_id] = failed
            self._roles[role_id] = replace(role, status=RoleStatus.FAILED)
            log_event(
                _log,
                "worker.failed",
                job_id=job_id,
                role_id=role_id,
                stage=stage.value,
                code=code,
                error_type=type(exc).__name__,
            )
            return failed
