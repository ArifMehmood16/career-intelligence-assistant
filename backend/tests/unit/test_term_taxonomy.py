"""Technology relations share document extraction and never become evidence."""

from __future__ import annotations

from career_assistant.application.contracts.taxonomy import TermRelations
from career_assistant.application.graph.taxonomy import edges_from_relations
from career_assistant.domain.knowledge_graph import NodeKind, Relation


def test_extracted_terms_open_only_inferred_graph_edges() -> None:
    edges = edges_from_relations(
        ["pgvector", "PGVECTOR", "python"],
        [
            TermRelations(
                term="pgvector",
                is_a=["Vector Database"],
                extends=["postgresql"],
                aliases=["pg_vector"],
            )
        ],
    )
    assert {
        (e.source.name, e.relation, e.target.kind, e.target.name) for e in edges
    } == {
        ("pgvector", Relation.IS_A, NodeKind.CATEGORY, "vector database"),
        ("pgvector", Relation.EXTENDS, NodeKind.TECHNOLOGY, "postgresql"),
        ("pg_vector", Relation.ALIAS_OF, NodeKind.TECHNOLOGY, "pgvector"),
    }
    assert all(edge.inferred and edge.cites_line is None for edge in edges)


def test_no_extracted_terms_open_no_edges() -> None:
    assert (
        edges_from_relations([], [TermRelations(term="python", is_a=["language"])])
        == ()
    )


def test_unrequested_terms_and_self_relations_are_ignored() -> None:
    edges = edges_from_relations(
        ["python"],
        [
            TermRelations(term="kubernetes", is_a=["orchestrator"]),
            TermRelations(term="python", aliases=["Python"], is_a=["language"]),
        ],
    )
    assert [(edge.source.name, edge.target.name) for edge in edges] == [
        ("python", "language")
    ]


def test_duplicate_relations_are_stored_once() -> None:
    item = TermRelations(term="python", is_a=["language", "Language"])
    assert len(edges_from_relations(["python"], [item, item])) == 1
