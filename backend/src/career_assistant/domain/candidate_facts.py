"""Facts about the candidate the judge reads beside the evidence (ADR 014).

Computed by domain code from the CV's graph, never by the model. Years count only
the advert's own spelling: an alias is reported as alias-only, because it is an
inferred link rather than something the CV writes.
"""

from __future__ import annotations

from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from career_assistant.domain.chunking import Chunk, TechTermProposal
from career_assistant.domain.experience import ExperienceFact
from career_assistant.domain.knowledge_graph import (
    NodeKind,
    Relation,
    experience_with,
    graph_from_chunks,
    normalise_term,
)
from career_assistant.domain.recency import DateRange


class Coverage(StrEnum):
    EXACT = "exact"
    ALIAS = "alias"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class TermFact:
    term: str
    coverage: Coverage
    experience: ExperienceFact


@dataclass(frozen=True, slots=True)
class RoleFact:
    title: str | None
    employer: str | None
    level: str | None
    dates: DateRange | None


@dataclass(frozen=True, slots=True)
class CandidateFacts:
    terms: tuple[TermFact, ...]
    roles: tuple[RoleFact, ...]


_EVIDENCE_RELATIONS = frozenset({Relation.USED, Relation.MENTIONS})


def candidate_facts(
    cv: Sequence[Chunk], terms: Sequence[TechTermProposal], *, as_of: date
) -> CandidateFacts:
    graph = graph_from_chunks(cv)
    named = {
        e.target.name
        for e in graph.edges
        if e.relation in _EVIDENCE_RELATIONS and e.target.kind is NodeKind.TECHNOLOGY
    }
    aliases = {
        (e.source.name, e.target.name)
        for e in graph.edges
        if e.relation is Relation.ALIAS_OF
    }
    facts: dict[str, TermFact] = {}
    for term in terms:
        surface = normalise_term(term.surface)
        if surface in facts:
            continue
        facts[surface] = TermFact(
            term=surface,
            coverage=_coverage(surface, normalise_term(term.canonical), named, aliases),
            experience=experience_with(graph, surface, as_of=as_of),
        )
    roles = tuple(
        RoleFact(
            title=node.properties.get("title"),
            employer=node.properties.get("employer"),
            level=node.properties.get("seniority_level"),
            dates=node.dates,
        )
        for node in graph.nodes
        if node.key.kind is NodeKind.ROLE
    )
    return CandidateFacts(terms=tuple(facts.values()), roles=roles)


def _coverage(
    surface: str,
    canonical: str,
    named: AbstractSet[str],
    aliases: AbstractSet[tuple[str, str]],
) -> Coverage:
    if surface in named:
        return Coverage.EXACT
    spellings = {surface, canonical}
    if canonical in named or any(
        written in named and spelled in spellings for written, spelled in aliases
    ):
        return Coverage.ALIAS
    return Coverage.MISSING
