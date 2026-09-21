"""PostgreSQL-backed in-process analysis worker — claim, extract, publish or fail."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from career_assistant.adapters.extraction.claims_rules import RulesClaimExtractor
from career_assistant.adapters.extraction.rules import RulesRequirementExtractor
from career_assistant.adapters.extraction.selected import (
    analysis_ports_for_choice,
)
from career_assistant.adapters.persistence.accounting import SqlCallAccountant
from career_assistant.adapters.persistence.embedding_repos import SqlEmbeddingCache
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.adapters.providers.factory import build_embedding_port
from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.application.analysis.relatedness import (
    NullAdjudicator,
    map_role_requirements,
)
from career_assistant.application.analysis.service import JobClock, StartupRecovery
from career_assistant.application.analysis.similarity import (
    requirement_claim_similarities,
)
from career_assistant.application.ports.adjudication import AdjudicationPort
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.errors import (
    EgressNotPermittedError,
    ProviderUnavailableError,
)
from career_assistant.application.ports.extraction import (
    ClaimExtractionPort,
    RequirementExtractionPort,
)
from career_assistant.application.providers.accounting import (
    AccountingEmbedding,
    CallAccountant,
)
from career_assistant.application.providers.catalogue import default_provider_choice
from career_assistant.application.scoring.rubric_loader import (
    load_mapping_config,
    load_scoring_rubric,
)
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
from career_assistant.domain.scoring import ScoringRubric, score_fit
from career_assistant.logconfig import log_event
from career_assistant.settings import ProviderSettings

_ROOT = Path(__file__).resolve().parents[5]
_DEFAULT_RUBRIC = load_scoring_rubric(_ROOT / "config" / "scoring_rubric.toml")
_MAPPING = load_mapping_config(_ROOT / "config" / "scoring_rubric.toml")
_DEFAULT_TIMEOUT = timedelta(minutes=15)
_log = logging.getLogger(__name__)


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
        providers: ProviderSettings | None = None,
        transport: HttpTransport | None = None,
        embedding_port: EmbeddingPort | None = None,
        call_accountant: CallAccountant | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._requirement_extractor = requirement_extractor
        self._claim_extractor = claim_extractor
        self._rubric = rubric or _DEFAULT_RUBRIC
        self._clock = clock or (lambda: datetime.now(UTC))
        self._running_timeout = running_timeout
        self._max_concurrent = max_concurrent
        self._providers = providers
        self._transport = transport
        self._embedding_port = embedding_port
        self._call_accountant = call_accountant

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
        log_event(
            _log,
            "worker.startup",
            failed_jobs=len(failed),
            dispatched_jobs=len(queued),
        )
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
            log_event(
                _log,
                "worker.claimed",
                job_id=claimed.id,
                role_id=claimed.role_id,
            )
            return claimed

    def complete(self, job: AnalysisJob) -> AnalysisJob:
        stage = JobStage.PARSING
        log_event(
            _log,
            "worker.stage",
            job_id=job.id,
            role_id=job.role_id,
            stage=stage.value,
        )
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
            log_event(
                _log,
                "worker.stage",
                job_id=job.id,
                role_id=job.role_id,
                stage=stage.value,
            )
            requirement_extractor, claim_extractor, adjudicator = (
                self._analysis_ports_for(job.workspace_id)
            )
            req_result = requirement_extractor.extract(
                document_id=jd_id,
                document_kind=DocumentKind.JOB_DESCRIPTION,
                normalised_text=jd_text,
            )
            stage = JobStage.EXTRACTING_CLAIMS
            log_event(
                _log,
                "worker.stage",
                job_id=job.id,
                role_id=job.role_id,
                stage=stage.value,
            )
            claim_result = claim_extractor.extract(
                document_id=cv_id,
                document_kind=DocumentKind.CV,
                normalised_text=cv_text,
            )
            stage = JobStage.MAPPING
            log_event(
                _log,
                "worker.stage",
                job_id=job.id,
                role_id=job.role_id,
                stage=stage.value,
            )
            embeddings, provider_id, model_tag = self._embedding_for(job.workspace_id)
            similarities = requirement_claim_similarities(
                workspace_id=job.workspace_id,
                requirements=req_result.requirements,
                claims=claim_result.claims,
                embedding=embeddings,
                cache=SqlEmbeddingCache(self._uow_factory),
                provider_id=provider_id,
                model_tag=model_tag,
            )
            mappings = map_role_requirements(
                req_result.requirements,
                claim_result.claims,
                similarities=similarities,
                adjudicator=adjudicator,
                similarity_floor=_MAPPING.similarity_floor,
            )
            stage = JobStage.SCORING
            log_event(
                _log,
                "worker.stage",
                job_id=job.id,
                role_id=job.role_id,
                stage=stage.value,
            )
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
            log_event(
                _log,
                "worker.succeeded",
                job_id=job.id,
                role_id=job.role_id,
                requirement_count=len(req_result.requirements),
                claim_count=len(claim_result.claims),
                mapping_count=len(mappings),
            )
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
        log_event(
            _log,
            "worker.failed",
            job_id=job.id,
            role_id=job.role_id,
            stage=stage.value,
            code=failed.error.code if failed.error else "unknown",
        )
        return failed

    def _analysis_ports_for(
        self, workspace_id: str
    ) -> tuple[RequirementExtractionPort, ClaimExtractionPort, AdjudicationPort]:
        if self._requirement_extractor is not None or self._claim_extractor is not None:
            return (
                self._requirement_extractor or RulesRequirementExtractor(),
                self._claim_extractor or RulesClaimExtractor(),
                NullAdjudicator(),
            )
        settings = self._providers or ProviderSettings(
            completion_provider="hermetic",
            embedding_provider="hermetic",
        )
        with self._uow_factory() as uow:
            choice = uow.provider_settings.get(workspace_id)
        if choice is None:
            choice = default_provider_choice(settings)
        return analysis_ports_for_choice(settings, choice, transport=self._transport)

    def _embedding_for(
        self, workspace_id: str
    ) -> tuple[EmbeddingPort | None, str, str]:
        settings = self._providers or ProviderSettings(
            completion_provider="hermetic",
            embedding_provider="hermetic",
        )
        with self._uow_factory() as uow:
            choice = uow.provider_settings.get(workspace_id)
        if choice is None:
            choice = default_provider_choice(settings)
        provider_id = choice.index_provider_id
        model_tag = choice.index_model
        if self._embedding_port is not None:
            return self._embedding_port, provider_id, model_tag
        try:
            port = build_embedding_port(
                settings,
                transport=self._transport,
                provider_id=provider_id,
                model_tag=model_tag,
            )
        except EgressNotPermittedError, ProviderUnavailableError:
            return None, provider_id, model_tag
        accountant = self._call_accountant or SqlCallAccountant(self._uow_factory)
        return (
            AccountingEmbedding(
                port,
                accountant,
                workspace_id=workspace_id,
                purpose="embed",
            ),
            provider_id,
            model_tag,
        )
