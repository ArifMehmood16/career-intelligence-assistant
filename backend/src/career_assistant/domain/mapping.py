"""Requirement-to-claim mapping — pure domain policy, no I/O."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum

from career_assistant.domain.claims import LISTED_DURATION, Claim
from career_assistant.domain.recency import covered_years, stated_years
from career_assistant.domain.relatedness import RelatednessSignals, pair_relatedness
from career_assistant.domain.requirements import Requirement


class MappingStatus(StrEnum):
    MET = "met"
    PARTIAL = "partial"
    MISSING = "missing"


class MappingReason(StrEnum):
    NO_RELATED_CLAIM = "no_related_claim"
    ADJACENT_CLAIM_ONLY = "adjacent_claim_only"
    EVIDENCE_TOO_OLD = "evidence_too_old"
    EVIDENCE_THIN = "evidence_thin"
    MATCHED = "matched"
    ASSESSMENT_INCOMPLETE = "assessment_incomplete"


@dataclass(frozen=True, slots=True)
class RequirementMapping:
    requirement_id: str
    status: MappingStatus
    reason_code: MappingReason
    justifying_span_ids: tuple[str, ...]
    justifying_claim_ids: tuple[str, ...]
    signals: RelatednessSignals = field(default_factory=RelatednessSignals)
    # Unknown or conflicting evidence is not full coverage. Scoring reads these;
    # a citation still does not prove the requirement is met.
    unknown_conditions: tuple[str, ...] = ()
    contradiction: bool = False
    # What the assessor was actually shown. A `missing` result means nothing
    # until this says whether the supporting claim was ever in the prompt.
    retrieved_claim_ids: tuple[str, ...] = ()
    # The model's own sentence for its assessment. Diagnostic only: a domain
    # rule can override the status afterwards, and then this no longer
    # describes the result.
    assessment_justification: str = ""


def map_requirements(
    requirements: tuple[Requirement, ...] | list[Requirement],
    claims: tuple[Claim, ...] | list[Claim],
    *,
    similarities: Mapping[tuple[str, str], float] | None = None,
    adjudications: Mapping[tuple[str, str], bool] | None = None,
    similarity_floor: float = 0.55,
) -> tuple[RequirementMapping, ...]:
    # Benefits, logistics and explicit non-requirements are kept for audit.
    # Only requirements and responsibilities are mapped and scored.
    # Self-authored cover letter claims are narrative: citable, never evidence.
    evidence = tuple(claim for claim in claims if not claim.self_authored)
    return tuple(
        map_requirement(
            req,
            evidence,
            similarities=similarities,
            adjudications=adjudications,
            similarity_floor=similarity_floor,
        )
        for req in requirements
        if req.is_scoreable
    )


def map_requirement(
    requirement: Requirement,
    claims: tuple[Claim, ...] | list[Claim],
    *,
    similarities: Mapping[tuple[str, str], float] | None = None,
    adjudications: Mapping[tuple[str, str], bool] | None = None,
    similarity_floor: float = 0.55,
) -> RequirementMapping:
    """Map one requirement to met/partial/missing with a reason and span ids."""
    decided = named_tool_mapping(requirement, claims)
    if decided is not None:
        return decided
    claims = tuple(
        claim for claim in claims if claim.duration_signal != LISTED_DURATION
    )
    sims = similarities or {}
    adjs = adjudications or {}
    considered: list[tuple[Claim, RelatednessSignals]] = []
    related: list[tuple[Claim, RelatednessSignals]] = []
    for claim in claims:
        key = (requirement.id, claim.id)
        signals = pair_relatedness(
            requirement,
            claim,
            similarity=sims.get(key, 0.0),
            similarity_floor=similarity_floor,
            adjudication=adjs[key] if key in adjs else None,
        )
        considered.append((claim, signals))
        if signals.related:
            related.append((claim, signals))
    if not related:
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.MISSING,
            reason_code=MappingReason.NO_RELATED_CLAIM,
            justifying_span_ids=(),
            justifying_claim_ids=(),
            signals=_closest_miss(considered),
        )

    same = [(c, s) for c, s in related if c.competency == requirement.competency]
    if not same:
        best, best_signals = _best_claim(related)
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.PARTIAL,
            reason_code=MappingReason.ADJACENT_CLAIM_ONLY,
            justifying_span_ids=best.source_span_ids,
            justifying_claim_ids=(best.id,),
            signals=best_signals,
        )

    recent_enough = [
        item for item in same if item[0].recency_signal in {"recent", "mid", "undated"}
    ]
    pool = recent_enough or same
    best, best_signals = _best_claim(pool)
    if not recent_enough and all(c.recency_signal == "old" for c, _s in same):
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.PARTIAL,
            reason_code=MappingReason.EVIDENCE_TOO_OLD,
            justifying_span_ids=best.source_span_ids,
            justifying_claim_ids=(best.id,),
            signals=best_signals,
        )

    if best_signals.lexical_overlap < 1 and requirement.competency == "general":
        return RequirementMapping(
            requirement_id=requirement.id,
            status=MappingStatus.PARTIAL,
            reason_code=MappingReason.EVIDENCE_THIN,
            justifying_span_ids=best.source_span_ids,
            justifying_claim_ids=(best.id,),
            signals=best_signals,
        )

    matched = RequirementMapping(
        requirement_id=requirement.id,
        status=MappingStatus.MET,
        reason_code=MappingReason.MATCHED,
        justifying_span_ids=best.source_span_ids,
        justifying_claim_ids=(best.id,),
        signals=best_signals,
    )
    limited = limit_concurrent_years(
        requirement, tuple(claim for claim, _signals in pool), matched
    )
    return course_does_not_meet_depth(requirement, claims, limited)


def limit_concurrent_years(
    requirement: Requirement,
    claims: tuple[Claim, ...] | list[Claim],
    mapping: RequirementMapping,
) -> RequirementMapping:
    """Do not treat overlapping jobs as separate years of coverage."""
    if mapping.status is not MappingStatus.MET:
        return mapping
    needed = stated_years(requirement.text)
    if needed is None:
        return mapping
    dated = tuple(
        claim
        for claim in claims
        if claim.period_start is not None and claim.competency == requirement.competency
    )
    covered = covered_years(dated)
    # Calendar spans land a fraction under a whole year. A month of slack
    # keeps back-to-back jobs that add up, and still rejects a real gap.
    if covered is None or covered >= needed - (1 / 12):
        return mapping
    span_ids = tuple(
        dict.fromkeys(span_id for claim in dated for span_id in claim.source_span_ids)
    )
    return replace(
        mapping,
        status=MappingStatus.PARTIAL,
        reason_code=MappingReason.EVIDENCE_THIN,
        justifying_span_ids=span_ids or mapping.justifying_span_ids,
        justifying_claim_ids=tuple(claim.id for claim in dated),
    )


# A named tool is the requirement's own words. This check keeps CI/CD and AWS;
# retrieval drops tokens of length 2, so it cannot be reused here.
_TOOL_TOKEN = re.compile(r"[a-z0-9]+(?:/[a-z0-9]+)*")
_TOOL_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "for",
        "with",
        "on",
        "in",
        "of",
        "to",
        "by",
        "at",
    }
)
# Years, leadership and outcome wording are not a bare tool name. A skills
# line cannot meet them, and neither can a token match.
_ASKS_FOR_MORE = re.compile(
    r"\b(?:lead\w*|design\w*|build\w*|contribut\w*|improv\w*|operat\w*|"
    r"own\w*|solv\w*|communicat\w*|collaborat\w*|mindset|background|"
    r"reliab\w*|startup|ambiguit\w*|devices?|real[- ]time)\b",
    re.IGNORECASE,
)


def named_tool_mapping(
    requirement: Requirement,
    claims: Sequence[Claim],
) -> RequirementMapping | None:
    """Met when the requirement only names a tool the CV actually lists.

    Returns None when this rule does not decide. A work bullet that contains
    the same words is the citation. A listed span cannot meet years,
    leadership or an outcome.
    """
    if _asks_for_more(requirement):
        if any(claim.duration_signal != LISTED_DURATION for claim in claims):
            return None
        return _tool_missing(requirement)
    match = _tool_citation(requirement, claims)
    if match is None:
        return None
    return _tool_met(requirement, match)


def _asks_for_more(requirement: Requirement) -> bool:
    signal = (requirement.seniority_signal or "").casefold()
    if stated_years(requirement.text) is not None or "lead" in signal:
        return True
    return _ASKS_FOR_MORE.search(requirement.text) is not None


def _tool_citation(requirement: Requirement, claims: Sequence[Claim]) -> Claim | None:
    needed = _tool_tokens(requirement.text)
    if not needed:
        return None
    matches = [
        claim
        for claim in claims
        if not claim.self_authored and needed <= _tool_tokens(claim.context)
    ]
    work = [claim for claim in matches if claim.duration_signal != LISTED_DURATION]
    # Old work stays on the existing recency path. A fresh bullet is the citation.
    fresh = [claim for claim in work if claim.recency_signal != "old"]
    if fresh:
        return max(fresh, key=lambda claim: len(claim.context))
    if work:
        return None
    if not matches:
        return None
    return max(matches, key=lambda claim: len(claim.context))


def _tool_met(requirement: Requirement, claim: Claim) -> RequirementMapping:
    return RequirementMapping(
        requirement_id=requirement.id,
        status=MappingStatus.MET,
        reason_code=MappingReason.MATCHED,
        justifying_span_ids=claim.source_span_ids,
        justifying_claim_ids=(claim.id,),
        signals=RelatednessSignals(
            lexical=True,
            lexical_overlap=1,
            embedding=False,
            embedding_similarity=0.0,
            adjudication=None,
            related=True,
        ),
    )


def _tool_tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOOL_TOKEN.findall(text.casefold())
        if token not in _TOOL_STOP and len(token) > 1
    }


def _tool_missing(requirement: Requirement) -> RequirementMapping:
    return RequirementMapping(
        requirement_id=requirement.id,
        status=MappingStatus.MISSING,
        reason_code=MappingReason.NO_RELATED_CLAIM,
        justifying_span_ids=(),
        justifying_claim_ids=(),
    )


_COURSE_TEXT = re.compile(
    r"\b(?:introductory|intro)\b.{0,40}\bcourse\b|\bcompleted\b.{0,40}\bcourse\b",
    re.IGNORECASE,
)


def course_does_not_meet_depth(
    requirement: Requirement,
    claims: Sequence[Claim],
    mapping: RequirementMapping,
) -> RequirementMapping:
    """An introductory course is not evidence for years of leadership."""
    if mapping.status is MappingStatus.MISSING:
        return mapping
    signal = (requirement.seniority_signal or "").casefold()
    asks_for_depth = stated_years(requirement.text) is not None or "lead" in signal
    if not asks_for_depth:
        return mapping
    cited_ids = set(mapping.justifying_claim_ids)
    cited = tuple(claim for claim in claims if claim.id in cited_ids)
    if not cited:
        cited = tuple(
            claim for claim in claims if claim.competency == requirement.competency
        )
    if not cited or not all(_is_course(claim) for claim in cited):
        return mapping
    return replace(
        mapping,
        status=MappingStatus.MISSING,
        reason_code=MappingReason.NO_RELATED_CLAIM,
        justifying_span_ids=(),
        justifying_claim_ids=(),
        signals=replace(mapping.signals, related=False),
    )


def _is_course(claim: Claim) -> bool:
    if claim.duration_signal == "course":
        return True
    return _COURSE_TEXT.search(claim.context) is not None


def _best_claim(
    items: list[tuple[Claim, RelatednessSignals]],
) -> tuple[Claim, RelatednessSignals]:
    rank = {"recent": 0, "mid": 1, "undated": 2, "old": 3}

    def key(item: tuple[Claim, RelatednessSignals]) -> tuple[int, int]:
        claim = item[0]
        return (rank.get(claim.recency_signal, 9), -len(claim.context))

    return sorted(items, key=key)[0]


def _closest_miss(
    items: list[tuple[Claim, RelatednessSignals]],
) -> RelatednessSignals:
    """Keep the strongest rejected pair so a veto still shows on the mapping."""
    if not items:
        return RelatednessSignals()
    return max(
        items,
        key=lambda item: (item[1].embedding_similarity, item[1].lexical_overlap),
    )[1]
