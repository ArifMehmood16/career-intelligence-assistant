"""Structured ask answers from stored mappings — pure domain, no retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from career_assistant.domain.intents import Intent
from career_assistant.domain.mapping import MappingStatus, RequirementMapping
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoreExplanation


class AnswerKind(StrEnum):
    ANSWER = "answer"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class AnswerCitation:
    span_id: str
    label: str


@dataclass(frozen=True, slots=True)
class AnswerResult:
    kind: AnswerKind
    content: str
    citations: tuple[AnswerCitation, ...]
    intent: Intent


@dataclass(frozen=True, slots=True)
class RoleAnalysisView:
    role_id: str
    title: str
    explanation: ScoreExplanation
    requirements: tuple[Requirement, ...]
    mappings: tuple[RequirementMapping, ...]
    span_texts: dict[str, str]


def validate_citations(
    result: AnswerResult,
    *,
    known_span_ids: frozenset[str],
) -> AnswerResult:
    """Drop answers that cite spans the server cannot resolve."""
    if result.kind is AnswerKind.INSUFFICIENT:
        return result
    if not result.citations:
        return result
    if all(c.span_id in known_span_ids for c in result.citations):
        return result
    return AnswerResult(
        kind=AnswerKind.INSUFFICIENT,
        content=("Not enough evidence in the stored documents to support that answer."),
        citations=(),
        intent=result.intent,
    )


def answer_structured(
    intent: Intent,
    question: str,
    *,
    roles: tuple[RoleAnalysisView, ...],
    known_span_ids: frozenset[str],
) -> AnswerResult:
    if intent is Intent.OPEN_QUESTION:
        raise ValueError("open questions must use retrieval, not answer_structured")
    if not roles:
        return AnswerResult(
            kind=AnswerKind.INSUFFICIENT,
            content="Not enough evidence — no analysed role is in scope.",
            citations=(),
            intent=intent,
        )

    if intent is Intent.COMPARE_ROLES:
        raw = _answer_compare(roles)
    elif intent is Intent.GAPS:
        raw = _answer_gaps(roles[0])
    elif intent is Intent.FIT:
        raw = _answer_fit(roles[0])
    elif intent is Intent.EVIDENCE_FOR_REQUIREMENT:
        raw = _answer_evidence(roles[0], question)
    elif intent is Intent.INTERVIEW_PREPARATION:
        raw = _answer_interview(roles[0])
    else:
        raw = AnswerResult(
            kind=AnswerKind.INSUFFICIENT,
            content="Not enough evidence for that question.",
            citations=(),
            intent=intent,
        )
    return validate_citations(raw, known_span_ids=known_span_ids)


def _reqs_by_id(view: RoleAnalysisView) -> dict[str, Requirement]:
    return {r.id: r for r in view.requirements}


def _maps_by_req(view: RoleAnalysisView) -> dict[str, RequirementMapping]:
    return {m.requirement_id: m for m in view.mappings}


def _cite(span_id: str, view: RoleAnalysisView) -> AnswerCitation:
    label = view.span_texts.get(span_id, span_id)[:80]
    return AnswerCitation(span_id=span_id, label=label)


def _answer_gaps(view: RoleAnalysisView) -> AnswerResult:
    reqs = _reqs_by_id(view)
    gaps: list[str] = []
    citations: list[AnswerCitation] = []
    for mapping in view.mappings:
        if mapping.status is MappingStatus.MET:
            continue
        req = reqs.get(mapping.requirement_id)
        label = req.text if req else mapping.requirement_id
        gaps.append(f"{label} ({mapping.status.value})")
        if req is not None:
            citations.append(_cite(req.source_span_id, view))
    if not gaps:
        return AnswerResult(
            kind=AnswerKind.ANSWER,
            content=f"No gaps for {view.title} — every mapped requirement is met.",
            citations=(),
            intent=Intent.GAPS,
        )
    body = (
        f"Gaps for {view.title}: "
        + "; ".join(gaps)
        + ". Close the highest-impact missing must-haves first."
    )
    return AnswerResult(
        kind=AnswerKind.ANSWER,
        content=body,
        citations=tuple(citations),
        intent=Intent.GAPS,
    )


def _answer_fit(view: RoleAnalysisView) -> AnswerResult:
    score = view.explanation.score
    band = view.explanation.band
    content = (
        f"Stored fit for {view.title} is {score:.0f} ({band}). "
        "This number comes from the mapping, not from a model judgement."
    )
    return AnswerResult(
        kind=AnswerKind.ANSWER,
        content=content,
        citations=(),
        intent=Intent.FIT,
    )


def _answer_evidence(view: RoleAnalysisView, question: str) -> AnswerResult:
    maps = _maps_by_req(view)
    q = question.lower()
    matched: Requirement | None = None
    for req in view.requirements:
        tokens = {t for t in req.competency.lower().split() if t}
        tokens.add(req.competency.lower())
        if any(token in q for token in tokens if len(token) > 1):
            matched = req
            break
        if req.text.lower()[:20] and req.text.lower()[:20] in q:
            matched = req
            break
    if matched is None:
        return AnswerResult(
            kind=AnswerKind.INSUFFICIENT,
            content="Not enough evidence — no matching requirement was found.",
            citations=(),
            intent=Intent.EVIDENCE_FOR_REQUIREMENT,
        )
    mapping = maps.get(matched.id)
    if mapping is None or mapping.status is MappingStatus.MISSING:
        return AnswerResult(
            kind=AnswerKind.INSUFFICIENT,
            content=(f"Not enough evidence in the CV for “{matched.text}”."),
            citations=(),
            intent=Intent.EVIDENCE_FOR_REQUIREMENT,
        )
    citations = tuple(_cite(span_id, view) for span_id in mapping.justifying_span_ids)
    if not citations:
        return AnswerResult(
            kind=AnswerKind.INSUFFICIENT,
            content=(f"Not enough evidence in the CV for “{matched.text}”."),
            citations=(),
            intent=Intent.EVIDENCE_FOR_REQUIREMENT,
        )
    excerpts = "; ".join(view.span_texts.get(c.span_id, c.label) for c in citations)
    return AnswerResult(
        kind=AnswerKind.ANSWER,
        content=f"Evidence for “{matched.text}”: {excerpts}",
        citations=citations,
        intent=Intent.EVIDENCE_FOR_REQUIREMENT,
    )


def _answer_interview(view: RoleAnalysisView) -> AnswerResult:
    reqs = _reqs_by_id(view)
    lines: list[str] = []
    citations: list[AnswerCitation] = []
    for mapping in view.mappings:
        req = reqs.get(mapping.requirement_id)
        if req is None or not req.must_have:
            continue
        lines.append(f"{req.text}: {mapping.status.value}")
        if mapping.justifying_span_ids:
            citations.extend(_cite(s, view) for s in mapping.justifying_span_ids)
        else:
            citations.append(_cite(req.source_span_id, view))
    content = f"Interview prep for {view.title}. Must-haves — " + "; ".join(lines) + "."
    return AnswerResult(
        kind=AnswerKind.ANSWER,
        content=content,
        citations=tuple(citations),
        intent=Intent.INTERVIEW_PREPARATION,
    )


def _answer_compare(roles: tuple[RoleAnalysisView, ...]) -> AnswerResult:
    ranked = sorted(roles, key=lambda r: r.explanation.score, reverse=True)
    ranking = ", ".join(f"{r.title} ({r.explanation.score:.0f})" for r in ranked)
    # Differentiating requirements: statuses that disagree across roles.
    all_req_ids = {m.requirement_id for r in roles for m in r.mappings}
    diffs: list[str] = []
    for req_id in sorted(all_req_ids):
        statuses = {
            next(
                (m.status for m in r.mappings if m.requirement_id == req_id),
                None,
            )
            for r in roles
        }
        statuses.discard(None)
        if len(statuses) > 1:
            label = req_id
            for role in roles:
                for requirement in role.requirements:
                    if requirement.id == req_id:
                        label = requirement.text
                        break
            diffs.append(label)
    if not diffs:
        # Same mapping shape — call out shared gaps as the contrast context.
        weakest = ranked[-1]
        by_id = _reqs_by_id(weakest)
        for mapping in weakest.mappings:
            if mapping.status is not MappingStatus.MET:
                gap_req = by_id.get(mapping.requirement_id)
                diffs.append(gap_req.text if gap_req else mapping.requirement_id)
    diff_text = "; ".join(diffs) if diffs else "none"
    content = (
        f"Ranking by stored fit scores: {ranking}. "
        f"Differentiating requirements: {diff_text}."
    )
    return AnswerResult(
        kind=AnswerKind.ANSWER,
        content=content,
        citations=(),
        intent=Intent.COMPARE_ROLES,
    )
