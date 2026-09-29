"""One v2 role analysis: index, match, score (ADR 013, ADR 014, PLAN 18.10).

The model chunks, relates terms and judges; the domain validates each verdict
and computes the score. A requirement the judge could not complete leaves the
whole analysis unscored.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from career_assistant.application.chunking.service import ChunkingRequest
from career_assistant.application.indexing.service import DocumentIndexer
from career_assistant.application.judge.candidate_search import HybridCandidateSearch
from career_assistant.application.judge.matching import EvidenceMatcher, MatchOutcome
from career_assistant.application.judge.service import RequirementJudge
from career_assistant.application.ports.chunks import StoredChunk
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.progress import NO_PROGRESS, AnalysisProgress
from career_assistant.application.ports.search import HybridSearchPort
from career_assistant.domain.candidate_facts import candidate_facts
from career_assistant.domain.chunking import TechTermProposal
from career_assistant.domain.judging import RequirementPacket
from career_assistant.domain.progress import TaskKey
from career_assistant.domain.recency import DateRange
from career_assistant.domain.scoring_v2 import (
    FitScoreV2,
    Gap,
    KeywordCoverage,
    RequirementToScore,
    RubricV2,
    gap_plan,
    keyword_coverage,
    score_v2,
)

# Requirement ids derive from the stored advert chunk, so they are stable while
# the advert's chunks are.
_REQUIREMENT_IDS = uuid.UUID("5d1c1f0e-6a52-4a43-9d0a-0f1b6c7e2a18")


@dataclass(frozen=True, slots=True)
class V2Documents:
    workspace_id: str
    cv: ChunkingRequest
    advert: ChunkingRequest
    as_of: date


@dataclass(frozen=True, slots=True)
class AnalysedRequirement:
    packet: RequirementPacket
    chunk_id: str
    position: int
    tech_terms: tuple[TechTermProposal, ...]


@dataclass(frozen=True, slots=True)
class V2Analysis:
    requirements: tuple[AnalysedRequirement, ...]
    match: MatchOutcome
    fit: FitScoreV2
    coverage: KeywordCoverage
    gaps: tuple[Gap, ...]
    left_machine: bool


@dataclass(frozen=True, slots=True)
class V2Limits:
    max_rewrites: int
    max_chars_per_text: int


class RoleAnalysisV2:
    def __init__(
        self,
        *,
        indexer: DocumentIndexer,
        judge: RequirementJudge,
        embedding: EmbeddingPort,
        search: HybridSearchPort,
        rubric: RubricV2,
        limits: V2Limits,
    ) -> None:
        self._indexer = indexer
        self._judge = judge
        self._embedding = embedding
        self._search = search
        self._rubric = rubric
        self._limits = limits

    def run(
        self, documents: V2Documents, *, progress: AnalysisProgress = NO_PROGRESS
    ) -> V2Analysis:
        ws, as_of = documents.workspace_id, documents.as_of
        progress.enter(TaskKey.READ_CV)
        cv = self._indexer.index(ws, documents.cv)
        progress.enter(TaskKey.READ_ADVERT)
        advert = self._indexer.index(ws, documents.advert)
        requirements = _requirements(advert.chunks)
        facts = candidate_facts(
            [s.chunk for s in cv.chunks],
            [t for r in requirements for t in r.tech_terms],
            as_of=as_of,
        )
        search = HybridCandidateSearch(
            workspace_id=ws,
            cv_chunks=cv.chunks,
            embedding=self._embedding,
            search=self._search,
            max_chars_per_text=self._limits.max_chars_per_text,
        )
        matcher = EvidenceMatcher(
            search, self._judge, max_rewrites=self._limits.max_rewrites
        )
        match = matcher.match(
            [r.packet for r in requirements], facts, as_of=as_of, progress=progress
        )
        progress.enter(TaskKey.SCORE)
        items = _to_score(requirements, match, _chunk_dates(cv.chunks))
        rubric, incomplete = self._rubric, match.incomplete
        return V2Analysis(
            requirements=requirements,
            match=match,
            fit=score_v2(items, rubric=rubric, as_of=as_of, incomplete=incomplete),
            coverage=keyword_coverage(facts),
            gaps=gap_plan(items, rubric=rubric, as_of=as_of, incomplete=incomplete),
            left_machine=cv.left_machine
            or advert.left_machine
            or any(record.left_machine for record in match.verdicts.values()),
        )


def _requirements(advert: Sequence[StoredChunk]) -> tuple[AnalysedRequirement, ...]:
    found: list[AnalysedRequirement] = []
    for stored in advert:
        for position, item in enumerate(stored.chunk.atomic_requirements):
            requirement_id = str(
                uuid.uuid5(_REQUIREMENT_IDS, f"{stored.chunk_id}:{position}")
            )
            found.append(
                AnalysedRequirement(
                    packet=RequirementPacket(
                        requirement_id=requirement_id,
                        quote=item.quote,
                        statement=item.statement,
                        must_have=item.must_have,
                        terms=tuple(t.surface for t in item.tech_terms),
                        candidates=(),
                        years_expected=item.years_expected,
                        seniority_expected=item.seniority_expected,
                    ),
                    chunk_id=stored.chunk_id,
                    position=position,
                    tech_terms=item.tech_terms,
                )
            )
    return tuple(found)


def _chunk_dates(cv: Sequence[StoredChunk]) -> dict[str, DateRange | None]:
    roles = {s.chunk.first_line: s.chunk.role for s in cv if s.chunk.role is not None}
    dates: dict[str, DateRange | None] = {}
    for stored in cv:
        role = roles.get(stored.chunk.role_ref) if stored.chunk.role_ref else None
        dates[stored.chunk_id] = role.dates if role is not None else None
    return dates


def _to_score(
    requirements: Sequence[AnalysedRequirement],
    match: MatchOutcome,
    dates: Mapping[str, DateRange | None],
) -> list[RequirementToScore]:
    items: list[RequirementToScore] = []
    for requirement in requirements:
        record = match.verdicts.get(requirement.packet.requirement_id)
        if record is None:
            continue
        items.append(
            RequirementToScore(
                requirement_id=requirement.packet.requirement_id,
                must_have=requirement.packet.must_have,
                verdict=record.verdict,
                cited_dates=tuple(
                    dates.get(quote.chunk_id) for quote in record.verdict.evidence
                ),
            )
        )
    return items
