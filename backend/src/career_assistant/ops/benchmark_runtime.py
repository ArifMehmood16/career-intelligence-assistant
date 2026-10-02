"""An explicit synthetic harness over the running analysis, never a product store."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from threading import Lock

from pydantic import BaseModel

from career_assistant.adapters.providers.factory import build_embedding_port
from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.adapters.providers.hermetic.index import (
    IndexBackedSearch,
    InMemoryIndexStore,
)
from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.providers.httpx_transport import HttpxTransport
from career_assistant.adapters.providers.structured_factory import build_structured_port
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
from career_assistant.application.ports.chunks import StoredChunk
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.progress import record_call
from career_assistant.application.ports.structured import (
    StructuredCompletionPort,
    StructuredRequest,
    StructuredResult,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    EmbeddingRequest,
    EmbeddingResult,
)
from career_assistant.application.ports.verdicts import VerdictRecord
from career_assistant.application.providers.accounting import (
    AccountingCompletion,
    AccountingEmbedding,
    CallAccountant,
)
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric_v2
from career_assistant.domain.documents import DocumentKind
from career_assistant.ops.benchmark_cases import ROOT, BenchmarkCase
from career_assistant.ops.benchmark_probe import (
    COMPLETION,
    EMBEDDING,
    STRUCTURED,
    BenchmarkProbe,
    MeasuredTransport,
)
from career_assistant.settings import ProviderSettings


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    repetitions: int = 1
    as_of: date = date(2026, 9, 1)
    live: bool = False
    provider: str = "hermetic"
    embedding_provider: str = "hermetic"
    completion_model: str | None = None
    embedding_model: str | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.repetitions <= 20:
            raise ValueError("repetitions_must_be_between_1_and_20")
        if self.live:
            if self.provider not in {"ollama", "openai", "anthropic"}:
                raise ValueError("live_completion_provider_required")
            if self.embedding_provider not in {"ollama", "openai"}:
                raise ValueError("live_embedding_provider_required")
        elif (
            self.provider != "hermetic"
            or self.embedding_provider != "hermetic"
            or self.completion_model is not None
            or self.embedding_model is not None
        ):
            raise ValueError("real_models_require_live_opt_in")


class _MeasuredStructured:
    def __init__(
        self, inner: StructuredCompletionPort, probe: BenchmarkProbe, *, fixture: bool
    ) -> None:
        self._inner, self._probe, self._fixture = inner, probe, fixture

    @property
    def capabilities(self) -> CapabilityDescriptor:
        value = self._inner.capabilities
        self._probe.capability(COMPLETION, value)
        return value

    def complete_structured[T: BaseModel](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]:
        self._probe.logical(STRUCTURED)
        try:
            result = self._inner.complete_structured(request)
        finally:
            if self._fixture:
                record_call("model")
        self._probe.observe(result.provider_id, result.model_tag, result.left_machine)
        return result


class _MeasuredEmbedding:
    def __init__(self, inner: EmbeddingPort, probe: BenchmarkProbe) -> None:
        self._inner, self._probe = inner, probe

    @property
    def capabilities(self) -> CapabilityDescriptor:
        value = self._inner.capabilities
        self._probe.capability(EMBEDDING, value)
        return value

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self._probe.logical(EMBEDDING)
        result = self._inner.embed(request)
        self._probe.observe(result.provider_id, result.model_tag, result.left_machine)
        return result


class _MeasuredIndex(InMemoryIndexStore):
    """Keep fixture storage semantics while observing actual reuse at the boundary."""

    def __init__(self, probe: BenchmarkProbe) -> None:
        super().__init__()
        self._probe = probe

    def find_chunks(
        self, workspace_id: str, document_id: str, *, prompt_version: str
    ) -> tuple[StoredChunk, ...]:
        chunks = super().find_chunks(
            workspace_id, document_id, prompt_version=prompt_version
        )
        if chunks:
            self._probe.reuse("documents")
        return chunks

    def embedded_chunk_ids(
        self, workspace_id: str, document_id: str, model_key: str
    ) -> frozenset[str]:
        ids = super().embedded_chunk_ids(workspace_id, document_id, model_key)
        self._probe.reuse("vectors", len(ids))
        return ids


class _MeasuredVerdictCache:
    def __init__(self, probe: BenchmarkProbe) -> None:
        self._probe = probe
        self._records: dict[str, VerdictRecord] = {}
        self._lock = Lock()

    def find(self, key: str) -> VerdictRecord | None:
        with self._lock:
            record = self._records.get(key)
        self._probe.reuse("verdict_lookups")
        if record is not None:
            self._probe.reuse("verdict_hits")
            self._probe.observe(
                record.provider_id, record.model_tag, record.left_machine
            )
        return record

    def keep(self, key: str, record: VerdictRecord) -> None:
        with self._lock:
            self._records[key] = record


@dataclass(frozen=True, slots=True)
class _Ports:
    structured: StructuredCompletionPort
    embedding: EmbeddingPort
    identity: ModelIdentity
    limits: V2Limits
    configuration: dict[str, object]


def _offline_ports(probe: BenchmarkProbe) -> _Ports:
    configuration: dict[str, object] = {
        "completion_provider": "hermetic",
        "completion_model": "rules-v1",
        "embedding_provider": "hermetic",
        "embedding_model": "lexical-hash-v1",
        "max_rewrites": 5,
        "max_embedding_chars": 8_000,
        "fallback_enabled": False,
    }
    probe.select(configuration)
    return _Ports(
        HermeticStructuredCompleter(),
        AccountingEmbedding(
            HermeticEmbeddingAdapter(),
            CallAccountant(),
            workspace_id="benchmark",
            purpose="analysis_benchmark",
        ),
        ModelIdentity("hermetic", "rules-v1"),
        V2Limits(5, 8_000),
        configuration,
    )


def _live_configuration(
    config: BenchmarkConfig, settings: ProviderSettings
) -> dict[str, object]:
    completion_models = {
        "ollama": settings.ollama_completion_model,
        "openai": settings.openai_completion_model,
        "anthropic": settings.anthropic_completion_model,
    }
    embedding_models = {
        "ollama": settings.ollama_embedding_model,
        "openai": settings.openai_embedding_model,
    }
    return {
        "completion_provider": config.provider,
        "completion_model": config.completion_model
        or completion_models[config.provider],
        "embedding_provider": config.embedding_provider,
        "embedding_model": config.embedding_model
        or embedding_models[config.embedding_provider],
        "max_rewrites": settings.judge_max_rewrites,
        "max_embedding_chars": settings.embedding_max_chars_per_text,
        "timeout_seconds": settings.provider_timeout_seconds,
        "max_retries": settings.provider_max_retries,
        "breaker_failure_threshold": settings.provider_breaker_failure_threshold,
        "hosted_max_in_flight": settings.hosted_max_in_flight,
        "fallback_enabled": False,
    }


def _live_ports(
    config: BenchmarkConfig, probe: BenchmarkProbe, transport: HttpTransport | None
) -> _Ports:
    settings = ProviderSettings().model_copy(
        update={"provider_allow_local_fallback": False}
    )
    configuration = _live_configuration(config, settings)
    probe.select(configuration)
    model = str(configuration["completion_model"])
    http, accountant = transport or HttpxTransport(), CallAccountant()
    structured = build_structured_port(
        settings,
        provider_id=config.provider,
        model_tag=model,
        transport=MeasuredTransport(http, probe, operation=COMPLETION),
        wrap=lambda port: AccountingCompletion(
            port, accountant, workspace_id="benchmark", purpose="analysis_benchmark"
        ),
    )
    embedding = AccountingEmbedding(
        build_embedding_port(
            settings,
            provider_id=config.embedding_provider,
            model_tag=str(configuration["embedding_model"]),
            transport=MeasuredTransport(http, probe, operation=EMBEDDING),
        ),
        accountant,
        workspace_id="benchmark",
        purpose="analysis_benchmark",
    )
    return _Ports(
        structured,
        embedding,
        ModelIdentity(config.provider, model),
        V2Limits(settings.judge_max_rewrites, settings.embedding_max_chars_per_text),
        configuration,
    )


class BenchmarkRuntime:
    def __init__(
        self,
        config: BenchmarkConfig,
        case: BenchmarkCase,
        probe: BenchmarkProbe,
        *,
        transport: HttpTransport | None = None,
    ) -> None:
        ports = (
            _live_ports(config, probe, transport)
            if config.live
            else _offline_ports(probe)
        )
        self._configuration = ports.configuration
        structured = _MeasuredStructured(
            ports.structured, probe, fixture=not config.live
        )
        embedding = _MeasuredEmbedding(ports.embedding, probe)
        store = _MeasuredIndex(probe)
        ws, cv_id, jd_id = "benchmark", f"{case.case_id}:cv", f"{case.case_id}:jd"
        self._documents = V2Documents(
            ws,
            ChunkingRequest(cv_id, DocumentKind.CV, case.cv_text),
            ChunkingRequest(jd_id, DocumentKind.JOB_DESCRIPTION, case.jd_text),
            config.as_of,
        )
        self._analysis = RoleAnalysisV2(
            indexer=DocumentIndexer(
                chunker=DocumentChunker(structured),
                embedding=embedding,
                store=store,
                max_chars_per_text=ports.limits.max_chars_per_text,
            ),
            judge=RequirementJudge(
                structured, _MeasuredVerdictCache(probe), ports.identity, JudgeLimits()
            ),
            embedding=embedding,
            search=IndexBackedSearch(
                store, ws, {cv_id: DocumentKind.CV, jd_id: DocumentKind.JOB_DESCRIPTION}
            ),
            rubric=load_scoring_rubric_v2(ROOT / "config/scoring_rubric.toml"),
            limits=ports.limits,
        )

    def run(self, probe: BenchmarkProbe) -> V2Analysis:
        probe.select(self._configuration)
        return self._analysis.run(self._documents, progress=probe)
