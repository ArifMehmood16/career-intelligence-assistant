"""Application-layer relatedness: gather the three signals, domain combines."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from career_assistant.application.ports.adjudication import (
    AdjudicationPair,
    AdjudicationPort,
    AssessmentEvidence,
    AssessmentItem,
)
from career_assistant.domain.assessment import EvidenceAssessment
from career_assistant.domain.claims import Claim
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
    course_does_not_meet_depth,
    limit_concurrent_years,
    map_requirements,
)
from career_assistant.domain.relatedness import (
    RelatednessSignals,
    lexical_overlap,
    pair_relatedness,
)
from career_assistant.domain.requirements import Requirement


@runtime_checkable
class SupportAssessor(Protocol):
    @property
    def decides_support(self) -> bool: ...

    def assess(
        self, items: Sequence[AssessmentItem]
    ) -> Mapping[str, EvidenceAssessment]: ...


def disagreement_pairs(
    requirements: Sequence[Requirement],
    claims: Sequence[Claim],
    *,
    similarities: Mapping[tuple[str, str], float],
    similarity_floor: float,
) -> tuple[AdjudicationPair, ...]:
    """Pairs where lexical overlap and embedding cosine disagree.

    Agreement (both related or both not) is already decided. Cover-letter
    claims and unscoreable items never reach the model.
    """
    pairs: list[AdjudicationPair] = []
    for requirement in requirements:
        if not requirement.is_scoreable:
            continue
        for claim in claims:
            if claim.self_authored:
                continue
            similarity = similarities.get((requirement.id, claim.id), 0.0)
            lexical = lexical_overlap(requirement.text, claim.context) >= 1
            embedding = similarity >= similarity_floor
            if lexical == embedding:
                continue
            pairs.append(
                AdjudicationPair(
                    requirement_id=requirement.id,
                    claim_id=claim.id,
                    requirement_text=requirement.text,
                    claim_context=claim.context,
                )
            )
    return tuple(pairs)


class NullAdjudicator:
    """Hermetic default: no model call. Domain falls back to OR on disagreement."""

    def assessment_source(self) -> tuple[str, str, bool]:
        return ("hermetic", "rules-v1", False)

    def adjudicate(
        self, pairs: Sequence[AdjudicationPair]
    ) -> Mapping[tuple[str, str], bool]:
        return {}


def map_role_requirements(
    requirements: Sequence[Requirement],
    claims: Sequence[Claim],
    *,
    similarities: Mapping[tuple[str, str], float] | None = None,
    adjudicator: AdjudicationPort,
    similarity_floor: float,
) -> tuple[RequirementMapping, ...]:
    sims = similarities or {}
    if isinstance(adjudicator, SupportAssessor) and adjudicator.decides_support:
        return _map_with_required_assessment(
            requirements,
            claims,
            similarities=sims,
            assessor=adjudicator,
            similarity_floor=similarity_floor,
        )
    pairs = disagreement_pairs(
        requirements,
        claims,
        similarities=sims,
        similarity_floor=similarity_floor,
    )
    adjudications: Mapping[tuple[str, str], bool] = (
        adjudicator.adjudicate(pairs) if pairs else {}
    )
    return map_requirements(
        tuple(requirements),
        tuple(claims),
        similarities=sims,
        adjudications=adjudications,
        similarity_floor=similarity_floor,
    )


def _map_with_required_assessment(
    requirements: Sequence[Requirement],
    claims: Sequence[Claim],
    *,
    similarities: Mapping[tuple[str, str], float],
    assessor: SupportAssessor,
    similarity_floor: float,
) -> tuple[RequirementMapping, ...]:
    """Retrieval still uses lexical overlap and embeddings.

    Every requirement with retrieved evidence is assessed, including when the
    two signals agree. No valid assessment means incomplete, not met.
    """
    claim_list = list(claims)
    prepared: list[tuple[Requirement, AssessmentItem | None, RelatednessSignals]] = []
    items: list[AssessmentItem] = []
    for requirement in requirements:
        if not requirement.is_scoreable:
            continue
        indexes = _retrieved_indexes(
            requirement,
            claim_list,
            similarities=similarities,
            similarity_floor=similarity_floor,
        )
        if not indexes:
            prepared.append((requirement, None, RelatednessSignals()))
            continue
        item = _assessment_item(
            requirement,
            claim_list,
            indexes,
            similarities,
            similarity_floor,
        )
        items.append(item)
        prepared.append(
            (
                requirement,
                item,
                _strongest_signals(
                    requirement,
                    claim_list,
                    indexes,
                    similarities=similarities,
                    similarity_floor=similarity_floor,
                ),
            )
        )
    assessments = assessor.assess(items) if items else {}
    mappings: list[RequirementMapping] = []
    for requirement, batch, signals in prepared:
        if batch is None:
            mappings.append(
                map_requirements(
                    (requirement,),
                    claim_list,
                    similarities=similarities,
                    similarity_floor=similarity_floor,
                )[0]
            )
            continue
        mappings.append(
            _mapping_from_assessment(
                requirement,
                claim_list,
                assessments.get(requirement.id),
                signals,
            )
        )
    return tuple(mappings)


def _retrieved_indexes(
    requirement: Requirement,
    claims: list[Claim],
    *,
    similarities: Mapping[tuple[str, str], float],
    similarity_floor: float,
) -> list[int]:
    hits: list[int] = []
    for index, claim in enumerate(claims):
        if claim.self_authored:
            continue
        similarity = similarities.get((requirement.id, claim.id), 0.0)
        lexical = lexical_overlap(requirement.text, claim.context) >= 1
        if lexical or similarity >= similarity_floor:
            hits.append(index)
    chosen: set[int] = set()
    for index in hits:
        for neighbor in (index - 1, index, index + 1):
            if 0 <= neighbor < len(claims) and not claims[neighbor].self_authored:
                chosen.add(neighbor)
    return sorted(chosen)


def _assessment_item(
    requirement: Requirement,
    claims: list[Claim],
    indexes: list[int],
    similarities: Mapping[tuple[str, str], float],
    similarity_floor: float,
) -> AssessmentItem:
    hit_ids = {
        claims[index].id
        for index in indexes
        if lexical_overlap(requirement.text, claims[index].context) >= 1
        or similarities.get((requirement.id, claims[index].id), 0.0) >= similarity_floor
    }
    conditions: list[str] = []
    if requirement.seniority_signal:
        conditions.append(f"seniority:{requirement.seniority_signal}")
    conditions.append("must_have" if requirement.must_have else "desirable")
    evidence = tuple(
        AssessmentEvidence(
            claim_id=claims[index].id,
            span_ids=claims[index].source_span_ids,
            text=claims[index].context,
            adjacent=claims[index].id not in hit_ids,
        )
        for index in indexes
    )
    return AssessmentItem(
        requirement_id=requirement.id,
        requirement_text=requirement.text,
        conditions=tuple(conditions),
        evidence=evidence,
    )


def _strongest_signals(
    requirement: Requirement,
    claims: list[Claim],
    indexes: list[int],
    *,
    similarities: Mapping[tuple[str, str], float],
    similarity_floor: float,
) -> RelatednessSignals:
    best = RelatednessSignals()
    best_key = (-1.0, -1.0)
    for index in indexes:
        claim = claims[index]
        signals = pair_relatedness(
            requirement,
            claim,
            similarity=similarities.get((requirement.id, claim.id), 0.0),
            similarity_floor=similarity_floor,
            adjudication=None,
        )
        key = (signals.embedding_similarity, float(signals.lexical_overlap))
        if key > best_key:
            best = signals
            best_key = key
    return best


def _mapping_from_assessment(
    requirement: Requirement,
    claims: list[Claim],
    assessment: EvidenceAssessment | None,
    signals: RelatednessSignals,
) -> RequirementMapping:
    if assessment is None:
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.MISSING,
            reason_code=MappingReason.ASSESSMENT_INCOMPLETE,
            justifying_span_ids=(),
            justifying_claim_ids=(),
            signals=RelatednessSignals(
                lexical=signals.lexical,
                lexical_overlap=signals.lexical_overlap,
                embedding=signals.embedding,
                embedding_similarity=signals.embedding_similarity,
                adjudication=None,
                related=False,
            ),
        )
    status = MappingStatus(assessment.status)
    if status is MappingStatus.MET:
        reason = MappingReason.MATCHED
    elif status is MappingStatus.PARTIAL:
        reason = MappingReason.EVIDENCE_THIN
    else:
        reason = MappingReason.NO_RELATED_CLAIM
    claim_ids = tuple(
        claim.id
        for claim in claims
        if any(
            span_id in assessment.supporting_span_ids
            for span_id in claim.source_span_ids
        )
    )
    mapped = RequirementMapping(
        requirement_id=requirement.id,
        status=status,
        reason_code=reason,
        justifying_span_ids=assessment.supporting_span_ids,
        justifying_claim_ids=claim_ids,
        unknown_conditions=assessment.unknown_conditions,
        contradiction=assessment.contradiction,
        signals=RelatednessSignals(
            lexical=signals.lexical,
            lexical_overlap=signals.lexical_overlap,
            embedding=signals.embedding,
            embedding_similarity=signals.embedding_similarity,
            adjudication=True,
            related=status is not MappingStatus.MISSING,
        ),
    )
    return course_does_not_meet_depth(
        requirement, claims, limit_concurrent_years(requirement, claims, mapped)
    )
