"""Hermetic sync analysis for in-memory role store — rules extractors only."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from career_assistant.adapters.extraction.claims_rules import RulesClaimExtractor
from career_assistant.adapters.extraction.rules import RulesRequirementExtractor
from career_assistant.application.analysis.similarity import (
    InMemoryEmbeddingCache,
    requirement_claim_similarities,
)
from career_assistant.application.ports.embedding import (
    EmbeddingCachePort,
    EmbeddingPort,
)
from career_assistant.application.ports.extraction import (
    ClaimExtractionPort,
    RequirementExtractionPort,
)
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric
from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import DocumentKind, Span
from career_assistant.domain.mapping import RequirementMapping, map_requirements
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoreExplanation, score_fit

_ROOT = Path(__file__).resolve().parents[5]
_RUBRIC = load_scoring_rubric(_ROOT / "config" / "scoring_rubric.toml")


@dataclass(frozen=True, slots=True)
class AnalysisBundle:
    requirements: tuple[Requirement, ...]
    claims: tuple[Claim, ...]
    mappings: tuple[RequirementMapping, ...]
    explanation: ScoreExplanation
    jd_document_id: str
    cv_document_id: str
    jd_spans: tuple[Span, ...] = ()
    cv_claim_spans: tuple[Span, ...] = ()


def analyse_hermetic(
    *,
    cv_text: str,
    cv_document_id: str,
    jd_text: str,
    requirement_extractor: RequirementExtractionPort | None = None,
    claim_extractor: ClaimExtractionPort | None = None,
    embedding: EmbeddingPort | None = None,
    embedding_cache: EmbeddingCachePort | None = None,
    embedding_provider_id: str = "hermetic",
    embedding_model_tag: str = "lexical-hash-v1",
    workspace_id: str = "hermetic",
) -> AnalysisBundle:
    jd_id = str(uuid.uuid4())
    req_result = (requirement_extractor or RulesRequirementExtractor()).extract(
        document_id=jd_id,
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=jd_text,
    )
    claim_result = (claim_extractor or RulesClaimExtractor()).extract(
        document_id=cv_document_id,
        document_kind=DocumentKind.CV,
        normalised_text=cv_text,
    )
    similarities = requirement_claim_similarities(
        workspace_id=workspace_id,
        requirements=req_result.requirements,
        claims=claim_result.claims,
        embedding=embedding,
        cache=embedding_cache or InMemoryEmbeddingCache(),
        provider_id=embedding_provider_id,
        model_tag=embedding_model_tag,
    )
    mappings = map_requirements(
        req_result.requirements,
        claim_result.claims,
        similarities=similarities,
    )
    explanation = score_fit(
        req_result.requirements, mappings, claim_result.claims, _RUBRIC
    )
    return AnalysisBundle(
        requirements=req_result.requirements,
        claims=claim_result.claims,
        mappings=mappings,
        explanation=explanation,
        jd_document_id=jd_id,
        cv_document_id=cv_document_id,
        jd_spans=req_result.spans,
        cv_claim_spans=claim_result.spans,
    )


def band_label(band: str) -> str:
    return {
        "strong": "Strong match",
        "partial": "Partial match",
        "limited": "Limited match",
    }.get(band, "Not scored yet")


def count_statuses(mappings: tuple[RequirementMapping, ...]) -> dict[str, int]:
    counts = {"met": 0, "partial": 0, "missing": 0}
    for mapping in mappings:
        counts[mapping.status.value] += 1
    return counts
