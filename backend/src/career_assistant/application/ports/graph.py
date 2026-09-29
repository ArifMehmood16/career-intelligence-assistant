"""Knowledge graph persistence and queries (ADR 013, PLAN 18.5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from career_assistant.domain.knowledge_graph import DocumentGraph, NodeKind, Relation
from career_assistant.domain.recency import DateRange


@dataclass(frozen=True, slots=True)
class TermUse:
    """An asserted use of a term exactly as the document wrote it, with its chunk."""

    relation: Relation
    chunk_id: str
    role_id: str | None
    role_title: str | None
    employer: str | None
    dates: DateRange | None


@dataclass(frozen=True, slots=True)
class RelatedTerm:
    """Reached through inferred edges only. Widens a search; never evidence."""

    name: str
    kind: NodeKind
    depth: int


class KnowledgeGraphRepository(Protocol):
    def replace_document_graph(
        self, workspace_id: str, document_id: str, graph: DocumentGraph
    ) -> None: ...

    def known_technologies(self, workspace_id: str) -> frozenset[str]: ...

    def term_uses(self, workspace_id: str, term: str) -> tuple[TermUse, ...]: ...

    def related_terms(
        self, workspace_id: str, term: str, *, depth: int = 2
    ) -> tuple[RelatedTerm, ...]: ...
