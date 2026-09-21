"""PostgreSQL-backed in-process analysis worker — claim, extract, publish or fail."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from career_assistant.adapters.extraction.claims_rules import RulesClaimExtractor
from career_assistant.adapters.extraction.rules import RulesRequirementExtractor
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.analysis.service import JobClock, StartupRecovery
from career_assistant.application.ports.extraction import (
    ClaimExtractionPort,
    RequirementExtractionPort,
)
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.jobs import (
    AnalysisJob,
    JobError,
    JobStage,
    JobState,
    mark_failed,
    mark_running,
    mark_stage,
    mark_succeeded,
    recover_stale_running,
)
from career_assistant.domain.mapping import map_requirements
from career_assistant.domain.scoring import ScoringRubric, score_fit

_ROOT = Path(__file__).resolve().parents[5]
_DEFAULT_RUBRIC = load_scoring_rubric(_ROOT / "config" / "scoring_rubric.toml")
_DEFAULT_TIMEOUT = timedelta(minutes=15)


class SqlAnalysisWorker:
    """Bounded in-process worker. Jobs live in PostgreSQL, not process memory."""

    def __init__(
        self,
        uow_factory: Callable[[], SqlUnitOfWork],
        *,
        requirement_extractor: RequirementExtractionPort | None = None,
        claim_extractor: ClaimExtractionPort | None = None,
        rubric: ScoringRubric | None = None,
        clock: JobClock | None = None,
        running_timeout: timedelta = _DEFAULT_TIMEOUT,
        max_concurrent: int = 1,
    ) -> None:
        self._uow_factory = uow_factory
        self._requirement_extractor = (
            requirement_extractor or RulesRequirementExtractor()
        )
        self._claim_extractor = claim_extractor or RulesClaimExtractor()
        self._rubric = rubric or _DEFAULT_RUBRIC
        self._clock = clock or (lambda: datetime.now(UTC))
        self._running_timeout = running_timeout
        self._max_concurrent = max_concurrent

    def startup(self) -> StartupRecovery:
        failed: list[str] = []
        with self._uow_factory() as uow:
            for job in uow.jobs.list_running():
                recovered = recover_stale_running(
                    job,
                    now=self._clock(),
                    running_timeout=self._running_timeout,
                )
                if recovered.state is JobState.FAILED:
                    uow.analysis.fail_job(
                        workspace_id=job.workspace_id,
                        role_id=job.role_id,
                        job=recovered,
                    )
                    failed.append(job.id)
            queued = uow.jobs.list_queued()
            uow.commit()
        return StartupRecovery(
            failed_job_ids=tuple(failed),
            dispatched_job_ids=tuple(job.id for job in queued),
        )

    def claim_next(self) -> AnalysisJob | None:
        with self._uow_factory() as uow:
            if len(uow.jobs.list_running()) >= self._max_concurrent:
                return None
            queued = uow.jobs.list_queued()
            if not queued:
                return None
            claimed = mark_running(queued[0], at=self._clock())
            uow.jobs.save(claimed)
            uow.commit()
            return claimed

    def complete(self, job: AnalysisJob) -> AnalysisJob:
        stage = JobStage.PARSING
        try:
            with self._uow_factory() as uow:
                role = uow.roles.get(job.workspace_id, job.role_id)
                if role is None:
                    raise RuntimeError("role_missing")
                jd = uow.documents.get(
                    job.workspace_id, role.job_description_document_id
                )
                if jd is None:
                    raise RuntimeError("jd_missing")
                cv = uow.documents.get_active_cv(job.workspace_id)
                if cv is None:
                    stage = JobStage.EXTRACTING_CLAIMS
                    raise RuntimeError("cv_missing")
                jd_id = jd.id
                jd_text = jd.normalised_text
                cv_id = cv.id
                cv_text = cv.normalised_text
                analysis_version = role.analysis_version

            stage = JobStage.EXTRACTING_REQUIREMENTS
            req_result = self._requirement_extractor.extract(
                document_id=jd_id,
                document_kind=DocumentKind.JOB_DESCRIPTION,
                normalised_text=jd_text,
            )
            stage = JobStage.EXTRACTING_CLAIMS
            claim_result = self._claim_extractor.extract(
                document_id=cv_id,
                document_kind=DocumentKind.CV,
                normalised_text=cv_text,
            )
            stage = JobStage.MAPPING
            mappings = map_requirements(req_result.requirements, claim_result.claims)
            stage = JobStage.SCORING
            explanation = score_fit(
                req_result.requirements,
                mappings,
                claim_result.claims,
                self._rubric,
            )

            running = (
                job
                if job.state is JobState.RUNNING
                else mark_running(job, at=self._clock())
            )
            terminal = mark_succeeded(
                mark_stage(running, JobStage.SCORING), at=self._clock()
            )
            with self._uow_factory() as uow:
                uow.documents.ensure_spans(job.workspace_id, jd_id, req_result.spans)
                uow.documents.ensure_spans(job.workspace_id, cv_id, claim_result.spans)
                uow.analysis.publish(
                    workspace_id=job.workspace_id,
                    role_id=job.role_id,
                    analysis_version=analysis_version,
                    cv_document_id=cv_id,
                    requirements=req_result.requirements,
                    claims=claim_result.claims,
                    mappings=mappings,
                    explanation=explanation,
                    job=terminal,
                )
                uow.commit()
            return terminal
        except Exception:
            return self._fail(job, stage)

    def process_next(self) -> AnalysisJob | None:
        claimed = self.claim_next()
        if claimed is None:
            return None
        return self.complete(claimed)

    def drain(self) -> None:
        while self.process_next() is not None:
            pass

    def run_forever(
        self, stop: threading.Event, *, idle_wait_seconds: float = 0.5
    ) -> None:
        self.startup()
        while not stop.is_set():
            processed = self.process_next()
            if processed is None:
                stop.wait(timeout=idle_wait_seconds)

    def _fail(self, job: AnalysisJob, stage: JobStage) -> AnalysisJob:
        with self._uow_factory() as uow:
            current = uow.jobs.get(job.workspace_id, job.id) or job
            running = (
                current
                if current.state is JobState.RUNNING
                else mark_running(current, at=self._clock())
            )
            failed = mark_failed(
                running,
                at=self._clock(),
                error=JobError(
                    code=f"{stage.value}_failed",
                    message="Analysis failed during this stage.",
                ),
            )
            uow.analysis.fail_job(
                workspace_id=job.workspace_id,
                role_id=job.role_id,
                job=failed,
            )
            uow.commit()
        return failed
