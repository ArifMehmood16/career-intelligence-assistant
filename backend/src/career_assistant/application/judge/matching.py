"""Search, judge, and correct once (ADR 014, PLAN 18.8).

Corrective retrieval is the workflow's one agentic decision: the judge may say its
evidence is not enough and name a better query. The workflow decides how much it
may look — one rewrite per requirement, and at most `max_rewrites` per analysis —
and both searches go into the trace.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from typing import Protocol

from career_assistant.application.judge.service import RequirementJudge
from career_assistant.application.ports.verdicts import VerdictRecord
from career_assistant.domain.candidate_facts import CandidateFacts
from career_assistant.domain.judging import Candidate, RequirementPacket
from career_assistant.domain.search import SearchHit


@dataclass(frozen=True, slots=True)
class CandidateSearchResult:
    hits: tuple[SearchHit, ...]
    candidates: tuple[Candidate, ...]


class CandidateSearch(Protocol):
    def find(
        self, requirement: RequirementPacket, query_text: str
    ) -> CandidateSearchResult: ...


@dataclass(frozen=True, slots=True)
class SearchRound:
    round: int
    query_text: str
    hits: tuple[SearchHit, ...]


@dataclass(frozen=True, slots=True)
class MatchOutcome:
    verdicts: Mapping[str, VerdictRecord]
    incomplete: tuple[str, ...]
    traces: Mapping[str, tuple[SearchRound, ...]]
    rewrites: int


class EvidenceMatcher:
    def __init__(
        self, search: CandidateSearch, judge: RequirementJudge, *, max_rewrites: int
    ) -> None:
        self._search = search
        self._judge = judge
        self._max_rewrites = max_rewrites

    def match(
        self,
        requirements: Sequence[RequirementPacket],
        facts: CandidateFacts,
        *,
        as_of: date,
    ) -> MatchOutcome:
        packets: list[RequirementPacket] = []
        traces: dict[str, tuple[SearchRound, ...]] = {}
        for requirement in requirements:
            found = self._search.find(requirement, requirement.statement)
            packets.append(replace(requirement, candidates=found.candidates))
            traces[requirement.requirement_id] = (
                SearchRound(0, requirement.statement, found.hits),
            )
        judged = self._judge.judge(packets, facts, as_of=as_of)
        verdicts = dict(judged.verdicts)
        rewrites = 0
        for packet in packets:
            if rewrites == self._max_rewrites:
                break
            record = verdicts.get(packet.requirement_id)
            query = _rewrite_query(record)
            if query is None:
                continue
            rewrites += 1
            found = self._search.find(packet, query)
            traces[packet.requirement_id] += (SearchRound(1, query, found.hits),)
            corrected = self._rejudge(packet, found, facts, as_of=as_of)
            if corrected is not None:
                verdicts[packet.requirement_id] = corrected
        return MatchOutcome(
            verdicts=verdicts,
            incomplete=judged.incomplete,
            traces=traces,
            rewrites=rewrites,
        )

    def _rejudge(
        self,
        packet: RequirementPacket,
        found: CandidateSearchResult,
        facts: CandidateFacts,
        *,
        as_of: date,
    ) -> VerdictRecord | None:
        """The first verdict stands when nothing new is found or this one fails."""
        seen = {c.chunk_id for c in packet.candidates}
        new = tuple(c for c in found.candidates if c.chunk_id not in seen)
        if not new:
            return None
        merged = replace(packet, candidates=packet.candidates + new)
        outcome = self._judge.judge([merged], facts, as_of=as_of)
        return outcome.verdicts.get(packet.requirement_id)


def _rewrite_query(record: VerdictRecord | None) -> str | None:
    if record is None or record.verdict.sufficient:
        return None
    query = (record.verdict.rewrite_query or "").strip()
    return query or None
