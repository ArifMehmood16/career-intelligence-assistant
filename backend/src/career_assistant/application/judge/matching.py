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
from career_assistant.application.ports.progress import (
    NO_PROGRESS,
    AnalysisProgress,
    progress_scope,
)
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

    def find_all(
        self, items: Sequence[tuple[RequirementPacket, str]]
    ) -> tuple[CandidateSearchResult, ...]: ...


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
        with progress_scope(progress, TaskKey.SEARCH):
            found = self._search.find_all(
                [(requirement, requirement.statement) for requirement in requirements]
            )
        for done, (requirement, result) in enumerate(
            zip(requirements, found, strict=True), start=1
        ):
            packets.append(replace(requirement, candidates=result.candidates))
            traces[requirement.requirement_id] = (
                SearchRound(0, requirement.statement, result.hits),
            )
            progress.count(TaskKey.SEARCH, done, total)
        progress.enter(TaskKey.JUDGE)
        with progress_scope(progress, TaskKey.JUDGE):
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
            with progress_scope(progress, TaskKey.RECHECK):
                self._rewrite(
                    wanted, facts, traces, verdicts, as_of=as_of, progress=progress
                )
        else:
            progress.skip(TaskKey.RECHECK)
        return MatchOutcome(
            verdicts=verdicts,
            incomplete=judged.incomplete,
            traces=traces,
            rewrites=len(wanted),
        )

    def _rewrite(
        self,
        wanted: Sequence[tuple[RequirementPacket, str]],
        facts: CandidateFacts,
        traces: dict[str, tuple[SearchRound, ...]],
        verdicts: dict[str, VerdictRecord],
        *,
        as_of: date,
        progress: AnalysisProgress,
    ) -> None:
        found = self._search.find_all(wanted)
        prepared: list[tuple[RequirementPacket, CandidateSearchResult]] = []
        for (packet, query), result in zip(wanted, found, strict=True):
            traces[packet.requirement_id] += (SearchRound(1, query, result.hits),)
            prepared.append((packet, result))
        outcomes = self._rejudge_all(prepared, facts, as_of=as_of, progress=progress)
        for requirement_id, corrected in outcomes:
            if corrected is not None:
                verdicts[requirement_id] = corrected

    def _rejudge_all(
        self,
        prepared: Sequence[tuple[RequirementPacket, CandidateSearchResult]],
        facts: CandidateFacts,
        *,
        as_of: date,
        progress: AnalysisProgress,
    ) -> list[tuple[str, VerdictRecord | None]]:
        # Requirements with new evidence share the model's normal batch planner.
        changed: list[RequirementPacket] = []
        for packet, result in prepared:
            seen = {candidate.chunk_id for candidate in packet.candidates}
            new = tuple(
                candidate
                for candidate in result.candidates
                if candidate.chunk_id not in seen
            )
            if new:
                changed.append(replace(packet, candidates=packet.candidates + new))
        total = len(prepared)
        skipped = total - len(changed)
        for handled in range(1, skipped + 1):
            progress.count(TaskKey.RECHECK, handled, total)
        if not changed:
            return []
        outcome = self._judge.judge(
            changed,
            facts,
            as_of=as_of,
            on_judged=lambda handled: progress.count(
                TaskKey.RECHECK, skipped + handled, total
            ),
        )
        # A failed rejudge preserves the original validated verdict.
        return [
            (packet.requirement_id, outcome.verdicts.get(packet.requirement_id))
            for packet in changed
        ]


def _rewrite_query(record: VerdictRecord | None) -> str | None:
    if record is None or record.verdict.sufficient:
        return None
    query = (record.verdict.rewrite_query or "").strip()
    return query or None
