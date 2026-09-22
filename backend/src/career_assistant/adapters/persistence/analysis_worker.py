"""PostgreSQL-backed in-process analysis worker — claim, extract, publish or fail."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

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
    load_rubric_version,
    load_scoring_rubric,
)
from career_assistant.domain.assessment import PROMPT_VERSION
from career_assistant.domain.attribution import (
    AnalysisAttribution,
    analysis_failure_status,
)
from career_assistant.domain.candidate_spans import spans_for_document
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
from career_assistant.domain.mapping import RequirementMapping
from career_assistant.domain.scoring import ScoringRubric, score_fit
from career_assistant.logconfig import (
    bind_request_context,
    clear_request_context,
    log_event,
    log_failure,
)
from career_assistant.settings import ProviderSettings

_ROOT = Path(__file__).resolve().parents[5]
_RUBRIC_PATH = _ROOT / "config" / "scoring_rubric.toml"
_DEFAULT_RUBRIC = load_scoring_rubric(_RUBRIC_PATH)
_RUBRIC_VERSION = load_rubric_version(_RUBRIC_PATH)
_MAPPING = load_mapping_config(_RUBRIC_PATH)
_DEFAULT_TIMEOUT = timedelta(minutes=15)
_log = logging.getLogger(__name__)


class JobCancelled(Exception):
    """The role was deleted while its analysis was still running."""


class DocumentReader(Protocol):
    def get(self, workspace_id: str, document_id: str) -> object | None: ...


class RoleReader(Protocol):
    def get(self, workspace_id: str, role_id: str) -> object | None: ...


def require_role(roles: RoleReader, workspace_id: str, role_id: str) -> None:
    """A deleted role is a cancellation, not an analysis failure.

    Hard delete removes the role, its job rows and its job description. The
    worker may already be past extraction. Writing spans then fails a foreign
    key, and recording that failure fails because the job row is gone too.
    """
    if roles.get(workspace_id, role_id) is None:
        raise JobCancelled(role_id)


def require_documents(
    documents: DocumentReader,
    workspace_id: str,
    document_ids: Sequence[str],
) -> None:
    """Fail by name when an upload the analysis started from has gone.

    Extraction runs for minutes between reading a document and writing its
    spans, and a replaced or deleted upload takes its row with it. Writing
    anyway raised a foreign-key violation from the driver, which says nothing
    about what happened.
    """
    missing = [
        document_id
        for document_id in document_ids
        if documents.get(workspace_id, document_id) is None
    ]
    if missing:
        raise RuntimeError("documents_changed")


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
        bind_request_context(
            correlation_id=job.id, workspace_id=job.workspace_id
        )
        try:
            return self._run_job(job)
        finally:
            clear_request_context()

    def _run_job(self, job: AnalysisJob) -> AnalysisJob:
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
            jd_spans = spans_for_document(jd_id, jd_text)
            cv_spans = spans_for_document(cv_id, cv_text)
            running = (
                job
                if job.state is JobState.RUNNING
                else mark_running(job, at=self._clock())
            )
            staged = mark_stage(running, JobStage.EXTRACTING_REQUIREMENTS)
            with self._uow_factory() as uow:
                require_role(uow.roles, job.workspace_id, job.role_id)
                require_documents(uow.documents, job.workspace_id, (jd_id, cv_id))
                uow.documents.ensure_spans(job.workspace_id, jd_id, jd_spans)
                uow.documents.ensure_spans(job.workspace_id, cv_id, cv_spans)
                uow.jobs.save(staged)
                uow.commit()
            job = staged
            log_event(
                _log,
                "worker.documents",
                job_id=job.id,
                role_id=job.role_id,
                jd_id=jd_id,
                cv_id=cv_id,
                jd_chars=len(jd_text),
                cv_chars=len(cv_text),
                jd_spans=len(jd_spans),
                cv_spans=len(cv_spans),
                analysis_version=analysis_version,
            )

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
            log_event(
                _log,
                "worker.requirements",
                job_id=job.id,
                role_id=job.role_id,
                complete=req_result.complete,
                requirements=len(req_result.requirements),
                spans=len(req_result.spans),
                dropped=req_result.dropped_unverifiable,
            )
            if not req_result.complete:
                running = (
                    job
                    if job.state is JobState.RUNNING
                    else mark_running(job, at=self._clock())
                )
                failed = mark_failed(
                    mark_stage(running, JobStage.EXTRACTING_REQUIREMENTS),
                    at=self._clock(),
                    error=JobError(
                        code="extraction_incomplete",
                        message=(
                            "Requirement extraction did not classify every part "
                            "of the job description. This is not a fit score."
                        ),
                    ),
                )
                with self._uow_factory() as uow:
                    require_role(uow.roles, job.workspace_id, job.role_id)
                    uow.analysis.fail_job(
                        workspace_id=job.workspace_id,
                        role_id=job.role_id,
                        job=failed,
                    )
                    uow.commit()
                log_failure(
                    _log,
                    "worker.failed",
                    job_id=job.id,
                    role_id=job.role_id,
                    stage=JobStage.EXTRACTING_REQUIREMENTS.value,
                    code="extraction_incomplete",
                    input=(
                        f"jd_id={jd_id},requirements={len(req_result.requirements)},"
                        f"spans={len(req_result.spans)},"
                        f"dropped={req_result.dropped_unverifiable}"
                    ),
                    requirements=len(req_result.requirements),
                    spans=len(req_result.spans),
                    dropped=req_result.dropped_unverifiable,
                )
                return failed
            stage = JobStage.EXTRACTING_CLAIMS
            job = mark_stage(job, stage)
            with self._uow_factory() as uow:
                require_role(uow.roles, job.workspace_id, job.role_id)
                uow.jobs.save(job)
                uow.commit()
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
            log_event(
                _log,
                "worker.claims",
                job_id=job.id,
                role_id=job.role_id,
                complete=claim_result.complete,
                spans_supplied=claim_result.spans_supplied,
                claims_returned=claim_result.claims_returned,
                claims_accepted=claim_result.claims_accepted,
                claims_rejected=claim_result.claims_rejected,
                roles_detected=claim_result.roles_detected,
                roles_without_claims=claim_result.roles_without_claims,
            )
            if not claim_result.complete:
                running = (
                    job
                    if job.state is JobState.RUNNING
                    else mark_running(job, at=self._clock())
                )
                failed = mark_failed(
                    mark_stage(running, JobStage.EXTRACTING_CLAIMS),
                    at=self._clock(),
                    error=JobError(
                        code="extraction_incomplete",
                        message=(
                            "Claim extraction could not classify scoreable "
                            "parts of the CV. This is not a fit score."
                        ),
                    ),
                )
                with self._uow_factory() as uow:
                    require_role(uow.roles, job.workspace_id, job.role_id)
                    uow.analysis.fail_job(
                        workspace_id=job.workspace_id,
                        role_id=job.role_id,
                        job=failed,
                    )
                    uow.commit()
                log_failure(
                    _log,
                    "worker.failed",
                    job_id=job.id,
                    role_id=job.role_id,
                    stage=JobStage.EXTRACTING_CLAIMS.value,
                    code="extraction_incomplete",
                    input=(
                        f"cv_id={cv_id},"
                        f"spans_supplied={claim_result.spans_supplied},"
                        f"claims_returned={claim_result.claims_returned},"
                        f"claims_accepted={claim_result.claims_accepted},"
                        f"claims_rejected={claim_result.claims_rejected},"
                        f"roles_detected={claim_result.roles_detected},"
                        f"roles_without_claims={claim_result.roles_without_claims}"
                    ),
                    spans_supplied=claim_result.spans_supplied,
                    claims_returned=claim_result.claims_returned,
                    claims_accepted=claim_result.claims_accepted,
                    claims_rejected=claim_result.claims_rejected,
                    roles_detected=claim_result.roles_detected,
                    roles_without_claims=claim_result.roles_without_claims,
                )
                return failed
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
            log_event(
                _log,
                "worker.mapping",
                job_id=job.id,
                role_id=job.role_id,
                mappings=len(mappings),
                requirements=len(req_result.requirements),
                claims=len(claim_result.claims),
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
            log_event(
                _log,
                "worker.scoring",
                job_id=job.id,
                role_id=job.role_id,
                band=explanation.band,
                numerator=explanation.numerator,
                denominator=explanation.denominator,
            )

            running = (
                job
                if job.state is JobState.RUNNING
                else mark_running(job, at=self._clock())
            )
            staged = mark_stage(running, JobStage.SCORING)
            if explanation.band == "incomplete":
                failed = mark_failed(
                    staged,
                    at=self._clock(),
                    error=JobError(
                        code="assessment_incomplete",
                        message=(
                            "Analysis did not assess every scoreable requirement. "
                            "This is not a fit score."
                        ),
                    ),
                )
                with self._uow_factory() as uow:
                    require_role(uow.roles, job.workspace_id, job.role_id)
                    uow.analysis.fail_job(
                        workspace_id=job.workspace_id,
                        role_id=job.role_id,
                        job=failed,
                    )
                    uow.commit()
                log_failure(
                    _log,
                    "worker.failed",
                    job_id=job.id,
                    role_id=job.role_id,
                    stage=stage.value,
                    code="assessment_incomplete",
                    input=(
                        f"band={explanation.band},"
                        f"numerator={explanation.numerator},"
                        f"denominator={explanation.denominator},"
                        f"mappings={len(mappings)},"
                        f"requirements={len(req_result.requirements)}"
                    ),
                    band=explanation.band,
                    numerator=explanation.numerator,
                    denominator=explanation.denominator,
                )
                return failed
            terminal = mark_succeeded(staged, at=self._clock())
            with self._uow_factory() as uow:
                require_role(uow.roles, job.workspace_id, job.role_id)
                require_documents(uow.documents, job.workspace_id, (jd_id, cv_id))
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
                    attribution=_attribution(adjudicator, mappings),
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
                dropped_unverifiable=req_result.dropped_unverifiable,
                band=explanation.band,
                numerator=explanation.numerator,
                denominator=explanation.denominator,
            )
            return terminal
        except JobCancelled:
            log_event(
                _log,
                "worker.cancelled",
                job_id=job.id,
                role_id=job.role_id,
            )
            return job
        except Exception as exc:
            return self._fail(job, stage, exc)

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
            try:
                processed = self.process_next()
            except Exception as error:
                # One job must not take the queue down with it.
                log_event(
                    _log,
                    "worker.job_error",
                    error_type=type(error).__name__,
                )
                stop.wait(timeout=idle_wait_seconds)
                continue
            if processed is None:
                stop.wait(timeout=idle_wait_seconds)

    def _fail(
        self, job: AnalysisJob, stage: JobStage, cause: BaseException | None = None
    ) -> AnalysisJob:
        try:
            return self._record_failure(job, stage, cause)
        except Exception as handler_error:
            # A handler that raises ends the worker thread, and every later job
            # stays queued with nothing shown anywhere. Recording the failure is
            # best effort; continuing is not.
            log_event(
                _log,
                "worker.fail_handler_error",
                job_id=job.id,
                role_id=job.role_id,
                stage=stage.value,
                error_type=type(handler_error).__name__,
            )
            return mark_failed(
                job,
                at=self._clock(),
                error=JobError(
                    code=f"{stage.value}_failed",
                    message="Analysis failed during this stage.",
                ),
            )

    def _record_failure(
        self, job: AnalysisJob, stage: JobStage, cause: BaseException | None = None
    ) -> AnalysisJob:
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
        log_failure(
            _log,
            "worker.failed",
            job_id=job.id,
            role_id=job.role_id,
            stage=stage.value,
            code=failed.error.code if failed.error else "unknown",
            error_type=type(cause).__name__ if cause is not None else "unknown",
            input=(
                f"stage={stage.value},"
                f"error_type={type(cause).__name__ if cause else 'unknown'}"
            ),
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
        accountant = self._call_accountant or SqlCallAccountant(self._uow_factory)
        return analysis_ports_for_choice(
            settings,
            choice,
            transport=self._transport,
            accountant=accountant,
            workspace_id=workspace_id,
        )

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
        except (EgressNotPermittedError, ProviderUnavailableError):
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


def _attribution(
    adjudicator: AdjudicationPort,
    mappings: Sequence[RequirementMapping],
) -> AnalysisAttribution:
    source = getattr(adjudicator, "assessment_source", None)
    if callable(source):
        provider, model, left_machine = source()
    else:
        provider, model, left_machine = "hermetic", "rules-v1", False
    prompt_version = (
        PROMPT_VERSION if getattr(adjudicator, "decides_support", False) else ""
    )
    return AnalysisAttribution(
        provider=str(provider),
        model=str(model),
        prompt_version=prompt_version,
        rubric_version=_RUBRIC_VERSION,
        left_machine=bool(left_machine),
        failure_status=analysis_failure_status(mappings),
    )
