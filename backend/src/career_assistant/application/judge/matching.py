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
from career_assistant.application.ports.progress import NO_PROGRESS, AnalysisProgress
from career_assistant.application.ports.verdicts import VerdictRecord
from career_assistant.domain.candidate_facts import CandidateFacts
from career_assistant.domain.judging import Candidate, RequirementPacket
from career_assistant.domain.progress import TaskKey
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
        progress: AnalysisProgress = NO_PROGRESS,
    ) -> MatchOutcome:
        total = len(requirements)
        progress.enter(TaskKey.SEARCH)
        progress.count(TaskKey.SEARCH, 0, total)
        packets: list[RequirementPacket] = []
        traces: dict[str, tuple[SearchRound, ...]] = {}
        for done, requirement in enumerate(requirements, start=1):
            found = self._search.find(requirement, requirement.statement)
            packets.append(replace(requirement, candidates=found.candidates))
            traces[requirement.requirement_id] = (
                SearchRound(0, requirement.statement, found.hits),
            )
            progress.count(TaskKey.SEARCH, done, total)
        progress.enter(TaskKey.JUDGE)
        judged = self._judge.judge(
            packets,
            facts,
            as_of=as_of,
            on_judged=lambda handled: progress.count(TaskKey.JUDGE, handled, total),
        )
        verdicts = dict(judged.verdicts)
        # Requirement order decides who gets the analysis's bounded rewrites.
        wanted = [
            (packet, query)
            for packet in packets
            if (query := _rewrite_query(verdicts.get(packet.requirement_id)))
        ][: self._max_rewrites]
        if wanted:
            progress.enter(TaskKey.RECHECK)
            progress.count(TaskKey.RECHECK, 0, len(wanted))
        else:
            progress.skip(TaskKey.RECHECK)
        for done, (packet, query) in enumerate(wanted, start=1):
            found = self._search.find(packet, query)
            traces[packet.requirement_id] += (SearchRound(1, query, found.hits),)
            corrected = self._rejudge(packet, found, facts, as_of=as_of)
            if corrected is not None:
                verdicts[packet.requirement_id] = corrected
            progress.count(TaskKey.RECHECK, done, len(wanted))
        return MatchOutcome(
            verdicts=verdicts,
            incomplete=judged.incomplete,
            traces=traces,
            rewrites=len(wanted),
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
