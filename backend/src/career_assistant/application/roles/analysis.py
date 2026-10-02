"""Views of the published chunk/verdict analysis for Ask and grounded drafts.

These projections never extract, assess or rescore. The published score and gap
lifts are reused by every reader.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from career_assistant.application.ports.chunks import StoredChunk
from career_assistant.application.ports.v2_results import V2RoleResult
from career_assistant.domain.attribution import AnalysisAttribution
from career_assistant.domain.candidate_spans import span_id
from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import Span
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoreComponent, ScoreExplanation
from career_assistant.domain.scoring_v2 import Gap


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
    attribution: AnalysisAttribution | None = None
    gaps: tuple[Gap, ...] = ()
    published_result: V2RoleResult | None = None


def chunk_span(stored: StoredChunk) -> Span:
    chunk = stored.chunk
    return Span(
        id=span_id(stored.document_id, chunk.start_offset, chunk.end_offset),
        document_id=stored.document_id,
        page_number=1,
        start_offset=chunk.start_offset,
        end_offset=chunk.end_offset,
        text=chunk.text,
    )


def published_bundle(
    *,
    result: V2RoleResult,
    chunks: Sequence[StoredChunk],
    explanation: ScoreExplanation,
    jd_document_id: str,
    cv_document_id: str,
    attribution: AnalysisAttribution | None = None,
) -> AnalysisBundle:
    by_id = {stored.chunk_id: stored for stored in chunks}
    spans = {key: chunk_span(stored) for key, stored in by_id.items()}
    requirements: list[Requirement] = []
    mappings: list[RequirementMapping] = []
    for item in result.verdicts:
        source = spans.get(item.source_chunk_id)
        if source is None or _collapse(item.quote) not in _collapse(source.text):
            raise ValueError("published_requirement_source_missing")
        requirements.append(
            Requirement(
                id=item.requirement_id,
                text=item.quote,
                competency=item.statement,
                seniority_signal="",
                must_have=item.must_have,
                source_span_id=source.id,
                extraction_confidence=1.0,
                is_vague=False,
            )
        )
        cited = tuple(dict.fromkeys(e.chunk_id for e in item.evidence))
        if any(
            key not in by_id or not by_id[key].chunk.evidence_eligible for key in cited
        ):
            raise ValueError("published_evidence_missing")
        if any(
            evidence.document_id != by_id[evidence.chunk_id].document_id
            or _collapse(evidence.quote) not in _collapse(by_id[evidence.chunk_id].chunk.text)
            for evidence in item.evidence
        ):
            raise ValueError("published_quote_missing")
        status = MappingStatus(item.verdict.verdict)
        mappings.append(
            RequirementMapping(
                requirement_id=item.requirement_id,
                status=status,
                reason_code=_reason(status),
                justifying_span_ids=tuple(spans[key].id for key in cited),
                justifying_claim_ids=cited,
                unknown_conditions=item.verdict.unmet_conditions,
                contradiction=item.verdict.contradiction,
            )
        )
    cited_ids = {key for mapping in mappings for key in mapping.justifying_claim_ids}
    claims = tuple(
        _claim(stored, spans[stored.chunk_id])
        for stored in chunks
        if stored.chunk_id in cited_ids
    )
    return AnalysisBundle(
        requirements=tuple(requirements),
        claims=claims,
        mappings=tuple(mappings),
        explanation=explanation,
        jd_document_id=jd_document_id,
        cv_document_id=cv_document_id,
        jd_spans=tuple(
            span
            for key, span in spans.items()
            if by_id[key].document_id == jd_document_id
        ),
        cv_claim_spans=tuple(spans[key] for key in cited_ids),
        attribution=attribution,
        gaps=result.gaps,
        published_result=result,
    )


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _claim(stored: StoredChunk, span: Span) -> Claim:
    chunk, role = stored.chunk, stored.chunk.role
    return Claim(
        id=stored.chunk_id,
        competency=chunk.kind,
        context=chunk.text,
        duration_signal="",
        recency_signal="undated",
        source_span_ids=(span.id,),
        extraction_confidence=1.0,
        employer=role.employer or "" if role else "",
        title=role.title or "" if role else "",
        technologies=tuple(term.surface for term in chunk.tech_terms),
    )


def _reason(status: MappingStatus) -> MappingReason:
    if status is MappingStatus.MET:
        return MappingReason.MATCHED
    if status is MappingStatus.PARTIAL:
        return MappingReason.EVIDENCE_THIN
    return MappingReason.NO_RELATED_CLAIM


def score_explanation(
    result: V2RoleResult, payload: Mapping[str, object]
) -> ScoreExplanation:
    statuses = {
        item.requirement_id: MappingStatus(item.verdict.verdict)
        for item in result.verdicts
    }
    raw = payload.get("requirement_scores", [])
    if not isinstance(raw, list):
        raise ValueError("published_components_missing")
    components = tuple(
        _component(item, statuses) for item in raw if isinstance(item, dict)
    )
    denominator = sum(item.weight for item in components)
    return ScoreExplanation(
        score=result.score,
        band=result.band,
        components=components,
        denominator=denominator,
        numerator=sum(item.contribution for item in components),
        publishable=True,
    )


def _component(
    item: Mapping[str, object], statuses: Mapping[str, MappingStatus]
) -> ScoreComponent:
    requirement_id = str(item["requirement_id"])
    return ScoreComponent(
        requirement_id=requirement_id,
        must_have=bool(item["must_have"]),
        status=statuses[requirement_id],
        weight=float(str(item["weight"])),
        status_factor=float(str(item["requirement_score"])),
        recency_factor=float(str(item["recency_factor"])),
        contribution=float(str(item["contribution"])),
        adjudicated=True,
    )


def band_label(band: str) -> str:
    return {
        "strong": "Strong match",
        "partial": "Partial match",
        "limited": "Limited match",
        "unscored": "Not scored yet",
    }.get(band, "Not scored yet")


def count_statuses(mappings: tuple[RequirementMapping, ...]) -> dict[str, int]:
    counts = {"met": 0, "partial": 0, "missing": 0}
    for mapping in mappings:
        counts[mapping.status.value] += 1
    return counts
