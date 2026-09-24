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
from career_assistant.domain.evidence_support import (
    is_evidence_context,
    is_evidential_support,
)
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
    course_does_not_meet_depth,
    limit_concurrent_years,
    map_requirements,
    named_tool_mapping,
)
from career_assistant.domain.relatedness import (
    RelatednessSignals,
    lexical_overlap,
    pair_relatedness,
)
from career_assistant.domain.requirements import Requirement

# How many claims one requirement may put in front of the assessor before
# neighbours are added. Small enough to keep the prompt and the call bounded.
_CANDIDATE_LIMIT = 5
# Below the paraphrase the retrieval tests keep (0.42) and above a claim with
# no shared keywords at 0.03. Not the 0.55 mapping floor. PLAN 14.7 calibrates it.
_RETRIEVAL_ABSTAIN_FLOOR = 0.35
# Requirement, optional assessment item, signals, and a domain decision.
_PreparedRequirement = tuple[
    Requirement,
    AssessmentItem | None,
    RelatednessSignals,
    RequirementMapping | None,
]


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
    A named tool the domain has already decided is not sent to the assessor.
    """
    claim_list = list(claims)
    prepared: list[_PreparedRequirement] = []
    items: list[AssessmentItem] = []
    for requirement in requirements:
        if not requirement.is_scoreable:
            continue
        decided = named_tool_mapping(requirement, claim_list)
        if decided is not None:
            prepared.append((requirement, None, RelatednessSignals(), decided))
            continue
        indexes = _retrieved_indexes(
            requirement,
            claim_list,
            similarities=similarities,
            similarity_floor=similarity_floor,
        )
        if not indexes:
            prepared.append((requirement, None, RelatednessSignals(), None))
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
                None,
            )
        )
    assessments = assessor.assess(items) if items else {}
    mappings: list[RequirementMapping] = []
    for requirement, batch, signals, decided in prepared:
        if decided is not None:
            mappings.append(decided)
            continue
        if batch is None:
            mappings.append(_no_evidence_mapping(requirement))
            continue
        mappings.append(
            _mapping_from_assessment(
                requirement,
                claim_list,
                assessments.get(requirement.id),
                signals,
                retrieved_claim_ids=tuple(
                    evidence.claim_id for evidence in batch.evidence
                ),
            )
        )
    return tuple(mappings)


def _no_evidence_mapping(requirement: Requirement) -> RequirementMapping:
    """Nothing eligible to show the assessor.

    Falling back to the lexical path here would let the superseded rules decide
    a requirement whenever retrieval returned nothing, which is exactly the
    failure this phase is closing. An empty candidate set is recorded instead.
    """
    return RequirementMapping(
        requirement_id=requirement.id,
        status=MappingStatus.MISSING,
        reason_code=MappingReason.NO_RELATED_CLAIM,
        justifying_span_ids=(),
        justifying_claim_ids=(),
        retrieved_claim_ids=(),
    )


def _retrieved_indexes(
    requirement: Requirement,
    claims: list[Claim],
    *,
    similarities: Mapping[tuple[str, str], float],
    similarity_floor: float,
) -> list[int]:
    """Shortlist the best few claims, or none when every signal is weak.

    The 0.55 mapping floor still does not decide missing: a paraphrase can sit
    under it and must reach the assessor. When the best claim has no lexical
    overlap and a measured similarity below the abstain floor, nothing is shown.
    Neighbours are added only after that check, to preserve negation and dates.
    """
    ranked = sorted(
        (
            -similarities.get((requirement.id, claim.id), 0.0),
            -lexical_overlap(requirement.text, claim.context),
            index,
        )
        for index, claim in enumerate(claims)
        if not claim.self_authored and is_evidential_support(claim.context)
    )
    if not ranked or _every_signal_is_weak(
        requirement, claims[ranked[0][2]], similarities, best_overlap=-ranked[0][1]
    ):
        return []
    chosen: set[int] = set()
    for _, _, index in ranked[:_CANDIDATE_LIMIT]:
        for neighbor in (index - 1, index, index + 1):
            if (
                0 <= neighbor < len(claims)
                and not claims[neighbor].self_authored
                and is_evidence_context(claims[neighbor].context)
            ):
                chosen.add(neighbor)
    return sorted(chosen)


def _every_signal_is_weak(
    requirement: Requirement,
    best: Claim,
    similarities: Mapping[tuple[str, str], float],
    *,
    best_overlap: int,
) -> bool:
    """No shared keyword and a measured similarity under the abstain floor.

    An absent similarity is not a weak one. With no embeddings (the hermetic
    path, or a closed hosted gate) abstaining would hide every paraphrase.
    """
    similarity = similarities.get((requirement.id, best.id))
    return (
        best_overlap < 1
        and similarity is not None
        and similarity < _RETRIEVAL_ABSTAIN_FLOOR
    )


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
            # Only the claim body is citable. Role headings travel with the claim
            # for provenance but must not become the evidence shown as Met.
            span_ids=(claims[index].source_span_ids[0],),
            text=claims[index].context,
            adjacent=claims[index].id not in hit_ids,
        )
        for index in indexes
        if claims[index].source_span_ids
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
    *,
    retrieved_claim_ids: tuple[str, ...],
) -> RequirementMapping:
    if assessment is None:
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.MISSING,
            reason_code=MappingReason.ASSESSMENT_INCOMPLETE,
            justifying_span_ids=(),
            justifying_claim_ids=(),
            retrieved_claim_ids=retrieved_claim_ids,
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
    evidential = _evidential_support(claims, assessment.supporting_span_ids)
    if status is not MappingStatus.MISSING and not evidential:
        # The model answered, but the cited text cannot justify support.
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.MISSING,
            reason_code=MappingReason.NO_RELATED_CLAIM,
            justifying_span_ids=(),
            justifying_claim_ids=(),
            retrieved_claim_ids=retrieved_claim_ids,
            assessment_justification=assessment.justification,
            unknown_conditions=assessment.unknown_conditions,
            contradiction=assessment.contradiction,
            signals=RelatednessSignals(
                lexical=signals.lexical,
                lexical_overlap=signals.lexical_overlap,
                embedding=signals.embedding,
                embedding_similarity=signals.embedding_similarity,
                adjudication=True,
                related=False,
            ),
        )
    claim_ids = tuple(claim.id for claim, _body in evidential)
    body_spans = tuple(body for _claim, body in evidential)
    mapped = RequirementMapping(
        requirement_id=requirement.id,
        status=status,
        reason_code=reason,
        justifying_span_ids=body_spans or assessment.supporting_span_ids,
        justifying_claim_ids=claim_ids,
        retrieved_claim_ids=retrieved_claim_ids,
        assessment_justification=assessment.justification,
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


def _evidential_support(
    claims: list[Claim],
    supporting_span_ids: tuple[str, ...],
) -> tuple[tuple[Claim, str], ...]:
    """Map cited ids onto claim bodies that can justify met or partial."""
    cited = set(supporting_span_ids)
    found: list[tuple[Claim, str]] = []
    for claim in claims:
        if not claim.source_span_ids:
            continue
        if not cited.intersection(claim.source_span_ids):
            continue
        if not is_evidential_support(claim.context):
            continue
        found.append((claim, claim.source_span_ids[0]))
    return tuple(found)
