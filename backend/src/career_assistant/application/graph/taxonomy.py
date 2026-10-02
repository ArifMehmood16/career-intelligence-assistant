"""Validate inferred technology relations returned with document extraction.

These edges widen retrieval and never become cited candidate evidence.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from career_assistant.application.contracts.taxonomy import TermRelations
from career_assistant.domain.knowledge_graph import (
    GraphEdge,
    NodeKey,
    NodeKind,
    Relation,
    normalise_term,
)


def edges_from_relations(
    terms: Sequence[str], relations: Sequence[TermRelations]
) -> tuple[GraphEdge, ...]:
    """Only extracted, server-validated terms may open inferred graph edges."""
    wanted = {normalise_term(term) for term in terms}
    edges = {
        edge: None
        for item in relations
        if normalise_term(item.term) in wanted
        for edge in _edges(item)
    }
    return tuple(edges)


def _edges(relations: TermRelations) -> Iterator[GraphEdge]:
    term = NodeKey(NodeKind.TECHNOLOGY, normalise_term(relations.term))
    targets = (
        (Relation.IS_A, NodeKind.CATEGORY, relations.is_a),
        (Relation.EXTENDS, NodeKind.TECHNOLOGY, relations.extends),
    )
    for relation, kind, names in targets:
        for name in names:
            other = NodeKey(kind, normalise_term(name))
            if other != term:
                yield GraphEdge(term, other, relation, None)
    for alias in relations.aliases:
        spelled = NodeKey(NodeKind.TECHNOLOGY, normalise_term(alias))
        if spelled != term:
            yield GraphEdge(spelled, term, Relation.ALIAS_OF, None)
