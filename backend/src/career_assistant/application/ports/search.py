"""Hybrid search over a workspace's evidence chunks (ADR 013, PLAN 18.6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.search import LegWeights, SearchHit

DEFAULT_SOURCES = (DocumentKind.CV, DocumentKind.COVER_LETTER)


@dataclass(frozen=True, slots=True)
class HybridQuery:
    """One search. `text` is the requirement as written; adapters remove the
    generic words with `lexical_query_text`, so every adapter shapes it alike."""

    workspace_id: str
    text: str
    embedding: tuple[float, ...]
    terms: tuple[str, ...]
    embedding_model_key: str
    sources: tuple[DocumentKind, ...] = DEFAULT_SOURCES
    match_count: int = 8
    leg_count: int = 20
    weights: LegWeights = field(default_factory=LegWeights)
    rrf_k: int = 60


class HybridSearchPort(Protocol):
    def search(self, query: HybridQuery) -> tuple[SearchHit, ...]: ...


@dataclass(frozen=True, slots=True)
class RetrievalTrace:
    """What the judge saw for one requirement: round 0, or 1 after a rewrite."""

    verdict_id: str
    round: int
    query_text: str
    hits: tuple[SearchHit, ...]


class RetrievalTraceRepository(Protocol):
    def save(self, workspace_id: str, trace: RetrievalTrace) -> None: ...

    def list_for_verdict(
        self, workspace_id: str, verdict_id: str
    ) -> tuple[RetrievalTrace, ...]: ...
