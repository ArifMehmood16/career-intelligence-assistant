"""The server's rules over a model judge's verdicts (ADR 014, PLAN 18.7).

A problem goes back to the model once. A cap is applied and recorded on the
verdict, so a reviewer can see where the server overruled the judge. Problems name
ids and fields only; they never repeat document text.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from career_assistant.domain.recency import DateRange

VerdictLabel = Literal["met", "partial", "missing"]


@dataclass(frozen=True, slots=True)
class Candidate:
    chunk_id: str
    kind: str
    source: str
    text: str
    role: str | None = None
    dates: DateRange | None = None


@dataclass(frozen=True, slots=True)
class JudgeDocumentContext:
    cv_document_id: str
    cv_text: str
    advert_document_id: str
    advert_text: str


@dataclass(frozen=True, slots=True)
class RequirementPacket:
    requirement_id: str
    quote: str
    statement: str
    must_have: bool
    terms: tuple[str, ...]
    candidates: tuple[Candidate, ...]
    years_expected: float | None = None
    seniority_expected: str | None = None
    experience_expected: str | None = None


@dataclass(frozen=True, slots=True)
class ProposedQuote:
    chunk_id: str
    quote: str


@dataclass(frozen=True, slots=True)
class ProposedScore:
    score: int
    rationale: str


@dataclass(frozen=True, slots=True)
class ProposedVerdict:
    requirement_id: str
    verdict: VerdictLabel
    match: ProposedScore
    evidence: tuple[ProposedQuote, ...] = ()
    seniority: ProposedScore | None = None
    experience: ProposedScore | None = None
    unmet_conditions: tuple[str, ...] = ()
    contradiction: bool = False
    sufficient: bool = True
    rewrite_query: str | None = None


class Adjustment(StrEnum):
    SKILLS_ONLY_MATCH = "match_capped_skills_only"
    SKILLS_ONLY_EXPERIENCE = "experience_capped_skills_only"
    CONTRADICTION_MATCH = "match_capped_contradiction"
    VERDICT_LOWERED = "verdict_lowered_to_partial"


@dataclass(frozen=True, slots=True)
class JudgedVerdict:
    requirement_id: str
    verdict: VerdictLabel
    match_score: int
    match_rationale: str
    evidence: tuple[ProposedQuote, ...]
    seniority: ProposedScore | None
    experience: ProposedScore | None
    unmet_conditions: tuple[str, ...]
    contradiction: bool
    sufficient: bool
    rewrite_query: str | None
    adjustments: tuple[Adjustment, ...]

    @property
    def experience_score(self) -> int | None:
        return None if self.experience is None else self.experience.score

    @property
    def seniority_score(self) -> int | None:
        return None if self.seniority is None else self.seniority.score


@dataclass(frozen=True, slots=True)
class JudgeCheck:
    verdicts: Mapping[str, JudgedVerdict]
    problems: Mapping[str, tuple[str, ...]]
    stray: tuple[str, ...] = ()


SKILLS_KIND = "skills"
_SKILLS_MATCH_CAP = 2
_BARE_TOOL_MATCH_CAP = 3
_SKILLS_EXPERIENCE_CAP = 1
_CONTRADICTION_MATCH_CAP = 2
_MET_FLOOR = 3


def check_verdicts(
    packets: Sequence[RequirementPacket], proposed: Sequence[ProposedVerdict]
) -> JudgeCheck:
    sent = {packet.requirement_id: packet for packet in packets}
    by_id: dict[str, list[ProposedVerdict]] = {}
    for verdict in proposed:
        by_id.setdefault(verdict.requirement_id, []).append(verdict)
    verdicts: dict[str, JudgedVerdict] = {}
    problems: dict[str, tuple[str, ...]] = {}
    for requirement_id, packet in sent.items():
        returned = by_id.get(requirement_id, [])
        found = _problems(packet, returned)
        if found:
            problems[requirement_id] = found
        else:
            verdicts[requirement_id] = _capped(packet, returned[0])
    stray = tuple(sorted(set(by_id) - set(sent)))
    return JudgeCheck(verdicts=verdicts, problems=problems, stray=stray)


def _problems(
    packet: RequirementPacket, returned: Sequence[ProposedVerdict]
) -> tuple[str, ...]:
    if not returned:
        return ("no verdict was returned",)
    if len(returned) > 1:
        return ("more than one verdict was returned",)
    verdict = returned[0]
    return (
        *_evidence_problems(packet, verdict),
        *_consistency_problems(verdict),
        *_dimension_problems(packet, verdict),
        *_feedback_problems(verdict),
    )


def _evidence_problems(
    packet: RequirementPacket, verdict: ProposedVerdict
) -> list[str]:
    texts = {c.chunk_id: _collapse(c.text) for c in packet.candidates}
    found: list[str] = []
    for index, quote in enumerate(verdict.evidence):
        text = texts.get(quote.chunk_id)
        if text is None:
            found.append(
                f"evidence[{index}]: chunk {quote.chunk_id} is not one of this "
                "requirement's candidates"
            )
        elif _collapse(quote.quote) not in text:
            found.append(
                f"evidence[{index}]: the quote is not in chunk {quote.chunk_id} "
                "word for word"
            )
    if verdict.match.score > 0 and not verdict.evidence:
        found.append("match: a score above 0 needs a quote")
    return found


def _consistency_problems(verdict: ProposedVerdict) -> list[str]:
    score = verdict.match.score
    if verdict.verdict == "missing" and score > 1:
        return ["verdict: missing needs a match score of 0 or 1"]
    if verdict.verdict != "missing" and score <= 1:
        return ["verdict: partial or met needs a match score of 2 or more"]
    if verdict.verdict == "met" and score < _MET_FLOOR:
        return ["verdict: met needs a match score of 3 or more"]
    return []


def _dimension_problems(
    packet: RequirementPacket, verdict: ProposedVerdict
) -> list[str]:
    checks = (
        ("seniority", "a level", packet.seniority_expected, verdict.seniority),
        (
            "experience",
            "years" if packet.years_expected is not None else "experience",
            packet.years_expected
            if packet.years_expected is not None
            else packet.experience_expected,
            verdict.experience,
        ),
    )
    found: list[str] = []
    for name, what, expected, scored in checks:
        if expected is not None and scored is None:
            found.append(f"{name}: the requirement states {what}, so score it")
        elif expected is None and scored is not None:
            found.append(
                f"{name}: the requirement states no {what.removeprefix('a ')}, "
                "so return null"
            )
    return found


def _feedback_problems(verdict: ProposedVerdict) -> list[str]:
    if verdict.sufficient or (verdict.rewrite_query or "").strip():
        return []
    return ["retrieval_feedback: rewrite_query is required when sufficient is false"]


def _capped(packet: RequirementPacket, verdict: ProposedVerdict) -> JudgedVerdict:
    match = verdict.match.score
    experience = verdict.experience
    adjustments: list[Adjustment] = []
    cited = _cited(packet, verdict)
    if cited and all(c.kind == SKILLS_KIND for c in cited):
        cap = _BARE_TOOL_MATCH_CAP if _bare_tool(packet, cited) else _SKILLS_MATCH_CAP
        if match > cap:
            match = cap
            adjustments.append(Adjustment.SKILLS_ONLY_MATCH)
        if experience is not None and experience.score > _SKILLS_EXPERIENCE_CAP:
            experience = ProposedScore(_SKILLS_EXPERIENCE_CAP, experience.rationale)
            adjustments.append(Adjustment.SKILLS_ONLY_EXPERIENCE)
    if verdict.contradiction and match > _CONTRADICTION_MATCH_CAP:
        match = _CONTRADICTION_MATCH_CAP
        adjustments.append(Adjustment.CONTRADICTION_MATCH)
    label = verdict.verdict
    if label == "met" and match < _MET_FLOOR:
        label = "partial"
        adjustments.append(Adjustment.VERDICT_LOWERED)
    return JudgedVerdict(
        requirement_id=verdict.requirement_id,
        verdict=label,
        match_score=match,
        match_rationale=verdict.match.rationale,
        evidence=verdict.evidence,
        seniority=verdict.seniority,
        experience=experience,
        unmet_conditions=verdict.unmet_conditions,
        contradiction=verdict.contradiction,
        sufficient=verdict.sufficient,
        rewrite_query=verdict.rewrite_query,
        adjustments=tuple(adjustments),
    )


def _cited(packet: RequirementPacket, verdict: ProposedVerdict) -> list[Candidate]:
    by_id = {c.chunk_id: c for c in packet.candidates}
    ids = dict.fromkeys(q.chunk_id for q in verdict.evidence)
    return [by_id[chunk_id] for chunk_id in ids]


def _bare_tool(packet: RequirementPacket, cited: Sequence[Candidate]) -> bool:
    """A named tool without years or seniority can be supported by a skills chunk."""
    if packet.years_expected is not None or packet.seniority_expected is not None:
        return False
    if not packet.terms:
        return False
    return any(
        all(find_term(c.text, term) is not None for term in packet.terms) for c in cited
    )


def find_term(text: str, term: str) -> str | None:
    """The term as the text writes it, ignoring case, never inside another word."""
    folded, wanted = text.casefold(), term.casefold()
    start = folded.find(wanted)
    while start >= 0:
        end = start + len(wanted)
        before = folded[start - 1] if start else " "
        after = folded[end] if end < len(folded) else " "
        if not before.isalnum() and not after.isalnum():
            return text[start:end]
        start = folded.find(wanted, start + 1)
    return None


def _collapse(value: str) -> str:
    return " ".join(value.split())
