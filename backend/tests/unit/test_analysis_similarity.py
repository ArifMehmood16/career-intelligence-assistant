"""Phase 13A.10 — embedding similarity for mapping candidates (application)."""

from __future__ import annotations

from dataclasses import dataclass, field

from tests.unit.test_analysis_pipeline import _service

from career_assistant.application.analysis.similarity import (
    InMemoryEmbeddingCache,
    requirement_claim_similarities,
)
from career_assistant.application.ports.extraction import (
    ClaimExtractionResult,
    RequirementExtractionResult,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    EmbeddingRequest,
    EmbeddingResult,
)
from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.jobs import JobState
from career_assistant.domain.mapping import MappingStatus
from career_assistant.domain.requirements import Requirement

_REQ = Requirement(
    id="req-k8s",
    text="Kubernetes cluster autoscaling",
    competency="kubernetes",
    seniority_signal=None,
    must_have=True,
    source_span_id="span-req",
    extraction_confidence=0.9,
    is_vague=False,
)
_CLAIM = Claim(
    id="claim-platform",
    competency="platform",
    context="Scaled container orchestration workloads across regions.",
    duration_signal="2y",
    recency_signal="recent",
    source_span_ids=("span-claim",),
    extraction_confidence=0.9,
)


class _AdjacentRequirements:
    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> RequirementExtractionResult:
        return RequirementExtractionResult(requirements=(_REQ,), spans=())


class _AdjacentClaims:
    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> ClaimExtractionResult:
        return ClaimExtractionResult(claims=(_CLAIM,), spans=())


@dataclass
class _ScriptedEmbedding:
    vectors: dict[str, tuple[float, ...]]
    calls: list[tuple[str, ...]] = field(default_factory=list)
    dimensions: int = 3
    provider_id: str = "scripted"
    model_tag: str = "scripted-v1"

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id=self.provider_id,
            supports_completion=False,
            supports_embedding=True,
            supports_structured_output=False,
            context_window_tokens=8192,
            max_output_tokens=0,
            embedding_dimensions=self.dimensions,
            leaves_machine=False,
        )

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.calls.append(request.texts)
        vectors = tuple(self.vectors[text] for text in request.texts)
        return EmbeddingResult(
            vectors=vectors,
            provider_id=self.provider_id,
            model_tag=self.model_tag,
            dimensions=self.dimensions,
            left_machine=False,
            input_tokens=len(request.texts),
            latency_ms=1,
        )


class _BoomEmbedding:
    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="boom",
            supports_completion=False,
            supports_embedding=True,
            supports_structured_output=False,
            context_window_tokens=8192,
            max_output_tokens=0,
            embedding_dimensions=3,
            leaves_machine=False,
        )

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        raise RuntimeError("embedding exploded")


def _aligned_scripted() -> _ScriptedEmbedding:
    vector = (1.0, 0.0, 0.0)
    return _ScriptedEmbedding(
        vectors={
            _REQ.text: vector,
            _CLAIM.context: vector,
        }
    )


def test_embedding_adapter_is_called_once_per_analysis_with_batched_texts() -> None:
    embedder = _aligned_scripted()
    cache = InMemoryEmbeddingCache()
    service, pub = _service(
        requirements=_AdjacentRequirements(),
        claims=_AdjacentClaims(),
        embedding=embedder,
        embedding_cache=cache,
        embedding_provider_id=embedder.provider_id,
        embedding_model_tag=embedder.model_tag,
    )
    service.create_role(
        workspace_id="ws-1", role_id="role-1", title="AE", job_id="job-1"
    )
    first = service.process_next()
    assert first is not None
    assert first.state is JobState.SUCCEEDED
    assert len(embedder.calls) == 1
    batched = embedder.calls[0]
    assert _REQ.text in batched
    assert _CLAIM.context in batched
    mapping = pub.published[0]["mappings"][0]  # type: ignore[index]
    assert mapping.status is not MappingStatus.MISSING
    assert mapping.signals.embedding is True
    assert mapping.signals.related is True

    again = service.enqueue_reanalysis(
        workspace_id="ws-1", role_id="role-1", job_id="job-2"
    )
    assert again.id == "job-2"
    second = service.process_next()
    assert second is not None
    assert second.state is JobState.SUCCEEDED
    assert len(embedder.calls) == 1


def test_embedding_failure_leaves_job_succeeded_without_similarity() -> None:
    service, pub = _service(
        requirements=_AdjacentRequirements(),
        claims=_AdjacentClaims(),
        embedding=_BoomEmbedding(),
        embedding_cache=InMemoryEmbeddingCache(),
        embedding_provider_id="boom",
        embedding_model_tag="boom-v1",
    )
    service.create_role(
        workspace_id="ws-1", role_id="role-1", title="AE", job_id="job-1"
    )
    done = service.process_next()
    assert done is not None
    assert done.state is JobState.SUCCEEDED
    mapping = pub.published[0]["mappings"][0]  # type: ignore[index]
    assert mapping.status is MappingStatus.MISSING


def test_requirement_claim_similarities_empty_when_port_missing() -> None:
    sims = requirement_claim_similarities(
        workspace_id="ws-1",
        requirements=(_REQ,),
        claims=(_CLAIM,),
        embedding=None,
        cache=InMemoryEmbeddingCache(),
        provider_id="hermetic",
        model_tag="lexical-hash-v1",
    )
    assert sims == {}
