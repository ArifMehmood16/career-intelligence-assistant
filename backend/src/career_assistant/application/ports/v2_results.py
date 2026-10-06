"""A published v2 analysis, as the API reads it back (PLAN 18.10)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from career_assistant.application.ports.search import RetrievalTrace
from career_assistant.domain.judging import JudgedVerdict
from career_assistant.domain.scoring_v2 import Gap, KeywordCoverage, RequirementScore


@dataclass(frozen=True, slots=True)
class StoredEvidence:
    chunk_id: str
    document_id: str
    quote: str


@dataclass(frozen=True, slots=True)
class StoredVerdict:
    requirement_id: str
    quote: str
    statement: str
    must_have: bool
    verdict: JudgedVerdict
    requirement_score: float | None
    evidence: tuple[StoredEvidence, ...]
    provider_id: str
    model_tag: str
    source_chunk_id: str = ""
    years_expected: float | None = None
    seniority_expected: str | None = None
    experience_expected: str | None = None


@dataclass(frozen=True, slots=True)
class V2RoleResult:
    analysis_id: str
    score: float
    band: str
    gated: bool
    rubric_version: str
    left_machine: bool
    verdicts: tuple[StoredVerdict, ...]
    coverage: KeywordCoverage
    gaps: tuple[Gap, ...]
    score_components: tuple[RequirementScore, ...] = ()


class V2ResultReader(Protocol):
    def result(self, workspace_id: str, role_id: str) -> V2RoleResult | None: ...

    def traces(
        self, workspace_id: str, role_id: str, requirement_id: str
    ) -> tuple[RetrievalTrace, ...] | None: ...
