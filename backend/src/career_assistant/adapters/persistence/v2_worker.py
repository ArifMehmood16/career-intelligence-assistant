"""The v2 analysis job: index, judge, score, publish (ADR 013, PLAN 18.10).

The worker runs every role analysis here. Model calls run outside
any transaction; each write opens its own unit of work. An analysis the judge
could not complete, or a document the chunker could not validate, fails the job
with a safe code and publishes no score.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from career_assistant.adapters.persistence.cancellation import SqlJobLiveness
from career_assistant.adapters.persistence.index_store import SqlDocumentIndexStore
from career_assistant.adapters.persistence.job_guards import (
    JobCancelled,
    require_documents,
    require_live_job,
)
from career_assistant.adapters.persistence.progress import sql_progress
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.adapters.persistence.v2_analysis_repos import (
    SqlVerdictCache,
    V2Publication,
)
from career_assistant.application.analysis.service import JobClock
from career_assistant.application.analysis.v2 import (
    RoleAnalysisV2,
    V2Analysis,
    V2Documents,
    V2Limits,
)
from career_assistant.application.chunking.service import (
    ChunkingIncompleteError,
    ChunkingRequest,
    DocumentChunker,
)
from career_assistant.application.indexing.service import DocumentIndexer
from career_assistant.application.judge.cache import ModelIdentity
from career_assistant.application.judge.prompt import JUDGE_PROMPT_VERSION, JudgeLimits
from career_assistant.application.judge.service import RequirementJudge
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.search import HybridQuery
from career_assistant.application.ports.structured import StructuredCompletionPort
from career_assistant.application.providers.cancellable import (
    CancellableEmbedding,
    CancellableStructured,
    CancellationCheck,
)
from career_assistant.domain.attribution import AnalysisAttribution
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
)
from career_assistant.domain.pipeline import PipelineVersion
from career_assistant.domain.progress import JobTask, TaskKey
from career_assistant.domain.scoring_v2 import RubricV2
from career_assistant.domain.search import SearchHit
from career_assistant.logconfig import log_event, log_failure

_log = logging.getLogger(__name__)

ASSESSMENT_INCOMPLETE = JobError(
    code="assessment_incomplete",
    message=(
        "Analysis did not assess every requirement in the job description. "
        "This is not a fit score."
    ),
)
EXTRACTION_INCOMPLETE = JobError(
    code="extraction_incomplete",
    message=(
        "A document could not be split into checked parts. This is not a fit score."
    ),
)


@dataclass(frozen=True, slots=True)
class V2Providers:
    structured: StructuredCompletionPort
    embedding: EmbeddingPort
    judge_model: ModelIdentity


@dataclass(frozen=True, slots=True)
class V2RunnerConfig:
    rubric: RubricV2
    limits: V2Limits
    clock: JobClock


FailJob = Callable[[AnalysisJob, JobStage, BaseException | None], AnalysisJob]


class UnitOfWorkHybridSearch:
    def __init__(self, uow_factory: Callable[[], SqlUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def search(self, query: HybridQuery) -> tuple[SearchHit, ...]:
        with self._uow_factory() as uow:
            return uow.search.search(query)


@dataclass(frozen=True, slots=True)
class _Loaded:
    documents: V2Documents
    analysis_version: int


class V2JobRunner:
    def __init__(
        self,
        uow_factory: Callable[[], SqlUnitOfWork],
        *,
        providers: Callable[[str], V2Providers],
        config: V2RunnerConfig,
        fail: FailJob,
    ) -> None:
        self._uow_factory = uow_factory
        self._providers = providers
        self._config = config
        self._fail = fail

    def run(self, job: AnalysisJob) -> AnalysisJob:
        stage = JobStage.PARSING
        progress = sql_progress(
            self._uow_factory, job, PipelineVersion.V2, self._config.clock
        )
        try:
            progress.enter(TaskKey.PREPARE)
            loaded = self._load(job)
            job = self._start(job)
            stage = JobStage.MAPPING
            providers = _cancellable(
                self._providers(job.workspace_id),
                SqlJobLiveness(self._uow_factory, job),
            )
            analysis = self._analysis(job.workspace_id, providers).run(
                loaded.documents, progress=progress
            )
            stage = JobStage.SCORING
            if not analysis.fit.publishable:
                return self._incomplete(job, stage, ASSESSMENT_INCOMPLETE)
            finished = progress.finished_tasks()
            return self._publish(job, loaded, analysis, providers, finished)
        except ChunkingIncompleteError:
            return self._incomplete(job, stage, EXTRACTION_INCOMPLETE)
        except JobCancelled:
            log_event(_log, "worker.cancelled", job_id=job.id, role_id=job.role_id)
            return job
        except Exception as exc:
            # The worker boundary: every other failure is recorded on the job.
            return self._fail(job, stage, exc)

    def _load(self, job: AnalysisJob) -> _Loaded:
        with self._uow_factory() as uow:
            role = uow.roles.get(job.workspace_id, job.role_id)
            if role is None:
                raise JobCancelled(job.role_id)
            advert = uow.documents.get(
                job.workspace_id, role.job_description_document_id
            )
            if advert is None:
                raise RuntimeError("jd_missing")
            cv = uow.documents.get_active_cv(job.workspace_id)
            if cv is None:
                raise RuntimeError("cv_missing")
            documents = V2Documents(
                workspace_id=job.workspace_id,
                cv=ChunkingRequest(
                    document_id=cv.id, kind=DocumentKind.CV, text=cv.normalised_text
                ),
                advert=ChunkingRequest(
                    document_id=advert.id,
                    kind=DocumentKind.JOB_DESCRIPTION,
                    text=advert.normalised_text,
                    advert_title=role.title,
                ),
                as_of=self._config.clock().date(),
            )
            return _Loaded(documents, role.analysis_version)

    def _start(self, job: AnalysisJob) -> AnalysisJob:
        running = (
            job
            if job.state is JobState.RUNNING
            else mark_running(job, at=self._config.clock())
        )
        staged = mark_stage(running, JobStage.MAPPING)
        with self._uow_factory() as uow:
            require_live_job(uow.jobs, job.workspace_id, job.id)
            uow.jobs.save(staged)
            uow.jobs.set_pipeline_version(job.workspace_id, job.id, PipelineVersion.V2)
            uow.commit()
        log_event(
            _log,
            "worker.stage",
            job_id=job.id,
            role_id=job.role_id,
            stage=JobStage.MAPPING.value,
            pipeline=PipelineVersion.V2.value,
        )
        return staged

    def _analysis(self, workspace_id: str, providers: V2Providers) -> RoleAnalysisV2:
        limits = self._config.limits
        return RoleAnalysisV2(
            indexer=DocumentIndexer(
                chunker=DocumentChunker(providers.structured),
                embedding=providers.embedding,
                store=SqlDocumentIndexStore(self._uow_factory),
                max_chars_per_text=limits.max_chars_per_text,
            ),
            judge=RequirementJudge(
                providers.structured,
                SqlVerdictCache(self._uow_factory, workspace_id),
                providers.judge_model,
                JudgeLimits(),
            ),
            embedding=providers.embedding,
            search=UnitOfWorkHybridSearch(self._uow_factory),
            rubric=self._config.rubric,
            limits=limits,
        )

    def _incomplete(
        self, job: AnalysisJob, stage: JobStage, error: JobError
    ) -> AnalysisJob:
        running = (
            job
            if job.state is JobState.RUNNING
            else mark_running(job, at=self._config.clock())
        )
        failed = mark_failed(
            mark_stage(running, stage), at=self._config.clock(), error=error
        )
        with self._uow_factory() as uow:
            require_live_job(uow.jobs, job.workspace_id, job.id)
            uow.analysis.fail_job(
                workspace_id=job.workspace_id, role_id=job.role_id, job=failed
            )
            uow.commit()
        log_failure(
            _log,
            "worker.failed",
            job_id=job.id,
            role_id=job.role_id,
            stage=stage.value,
            code=error.code,
            input=f"pipeline={PipelineVersion.V2.value},stage={stage.value}",
        )
        return failed

    def _publish(
        self,
        job: AnalysisJob,
        loaded: _Loaded,
        analysis: V2Analysis,
        providers: V2Providers,
        tasks: tuple[JobTask, ...],
    ) -> AnalysisJob:
        terminal = mark_succeeded(job, at=self._config.clock())
        documents = loaded.documents
        with self._uow_factory() as uow:
            require_live_job(uow.jobs, job.workspace_id, job.id)
            require_documents(
                uow.documents,
                job.workspace_id,
                (documents.cv.document_id, documents.advert.document_id),
            )
            uow.v2.publish(
                V2Publication(
                    workspace_id=job.workspace_id,
                    role_id=job.role_id,
                    analysis_version=loaded.analysis_version,
                    job=terminal,
                    analysis=analysis,
                    rubric_version=self._config.rubric.version,
                    attribution=AnalysisAttribution(
                        provider=providers.judge_model.provider_id,
                        model=providers.judge_model.model_tag,
                        prompt_version=JUDGE_PROMPT_VERSION,
                        rubric_version=self._config.rubric.version,
                        left_machine=analysis.left_machine,
                        failure_status=None,
                    ),
                )
            )
            uow.job_tasks.put(job.workspace_id, job.id, tasks)
            uow.commit()
        log_event(
            _log,
            "worker.succeeded",
            job_id=job.id,
            role_id=job.role_id,
            pipeline=PipelineVersion.V2.value,
            requirement_count=len(analysis.requirements),
            rewrites=analysis.match.rewrites,
            band=analysis.fit.band,
        )
        return terminal


def _cancellable(providers: V2Providers, check: CancellationCheck) -> V2Providers:
    """No provider call starts once the role or the CV has been deleted."""
    return V2Providers(
        structured=CancellableStructured(providers.structured, check),
        embedding=CancellableEmbedding(providers.embedding, check),
        judge_model=providers.judge_model,
    )
