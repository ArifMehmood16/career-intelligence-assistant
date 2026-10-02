"""Judge contract: one verdict per atomic requirement (ADR 014).

Shape only. The server's rules — cited ids within the candidate set, verbatim
quotes, verdict and match consistency, null dimensions, caps — run in domain code
after this parses.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from career_assistant.application.contracts.base import (
    Contract,
    NonEmpty,
    VersionedContract,
)

Score = Annotated[int, Field(ge=0, le=4)]


class EvidenceQuote(Contract):
    chunk_id: NonEmpty
    quote: NonEmpty = Field(description="Words copied exactly from that chunk.")


class MatchJudgement(Contract):
    score: Score
    rationale: NonEmpty = Field(max_length=600)
    evidence: list[EvidenceQuote] = Field(default_factory=list)


class DimensionJudgement(Contract):
    score: Score
    rationale: NonEmpty = Field(max_length=600)


class RetrievalFeedback(Contract):
    sufficient: bool
    rewrite_query: str | None = Field(
        default=None, max_length=300, description="Required when sufficient is false."
    )


class RequirementVerdict(Contract):
    requirement_id: NonEmpty
    verdict: Literal["met", "partial", "missing"]
    match: MatchJudgement
    seniority: DimensionJudgement | None = None
    experience: DimensionJudgement | None = None
    unmet_conditions: list[NonEmpty] = Field(default_factory=list)
    contradiction: bool = False
    retrieval_feedback: RetrievalFeedback


class JudgeResponse(VersionedContract):
    contract_version = "judge-v1"
    verdicts: list[RequirementVerdict] = Field(min_length=1)
