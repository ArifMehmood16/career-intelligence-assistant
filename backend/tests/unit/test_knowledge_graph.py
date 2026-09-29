"""The knowledge graph built from validated chunks (ADR 013, PLAN 18.5).

Asserted edges come from a chunk and cite it. Inferred edges — the chunker's
canonical spellings here, the taxonomy call later — cite nothing, and never count
as the candidate's evidence or as an exact match.
"""

from __future__ import annotations

from datetime import date

import pytest

from career_assistant.domain.chunking import (
    AtomicRequirementProposal,
    ProposedChunk,
    RoleProposal,
    TechTermProposal,
    validate_chunk_plan,
)
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.knowledge_graph import (
    GraphEdge,
    NodeKey,
    NodeKind,
    Relation,
    experience_with,
    graph_from_chunks,
)
from career_assistant.domain.lines import number_lines

CV = (
    "Senior Data Engineer, Northwind, Mar 2021 – Dec 2024\n"
    "Built retrieval over Postgres and Python.\n"
    "Software Engineer, Acme, Jun 2018 – Feb 2021\n"
    "Wrote Python services.\n"
    "Skills: Kafka\n"
)
JD = "5+ years of Python and Postgres\n"


def _tech(surface: str, canonical: str | None = None) -> TechTermProposal:
    return TechTermProposal(surface=surface, canonical=canonical or surface.lower())


def _role(line: int, title: str, employer: str, dates: str) -> ProposedChunk:
    return ProposedChunk(
        first_line=line,
        last_line=line,
        kind="role_heading",
        role=RoleProposal(employer=employer, title=title, date_text=dates),
    )


def _cv_graph():  # noqa: ANN202
    plan = validate_chunk_plan(
        DocumentKind.CV,
        number_lines(CV),
        CV,
        [
            _role(1, "Senior Data Engineer", "Northwind", "Mar 2021 – Dec 2024"),
            ProposedChunk(
                first_line=2,
                last_line=2,
                kind="experience",
                role_ref=1,
                tech_terms=(_tech("Postgres", "postgresql"), _tech("Python")),
            ),
            _role(3, "Software Engineer", "Acme", "Jun 2018 – Feb 2021"),
            ProposedChunk(
                first_line=4,
                last_line=4,
                kind="experience",
                role_ref=3,
                tech_terms=(_tech("Python"),),
            ),
            ProposedChunk(
                first_line=5, last_line=5, kind="skills", tech_terms=(_tech("Kafka"),)
            ),
        ],
    )
    assert plan.problems == ()
    return graph_from_chunks(plan.chunks)


def _tech_key(name: str) -> NodeKey:
    return NodeKey(NodeKind.TECHNOLOGY, name)


def _edges(graph, relation: Relation) -> list[GraphEdge]:  # noqa: ANN001
    return [e for e in graph.edges if e.relation is relation]


def test_a_role_used_each_technology_its_bullets_name_citing_the_bullet() -> None:
    graph = _cv_graph()

    used = {
        (e.source.name, e.target.name, e.cites_line)
        for e in _edges(graph, Relation.USED)
    }

    assert used == {
        ("senior data engineer at northwind (line 1)", "postgres", 2),
        ("senior data engineer at northwind (line 1)", "python", 2),
        ("software engineer at acme (line 3)", "python", 4),
    }


def test_a_role_is_at_its_employer_citing_the_heading() -> None:
    at = {
        (e.source.name, e.target.name, e.cites_line)
        for e in _edges(_cv_graph(), Relation.AT)
    }

    assert ("senior data engineer at northwind (line 1)", "northwind", 1) in at


def test_a_role_node_carries_its_parsed_dates() -> None:
    graph = _cv_graph()
    role = next(
        n
        for n in graph.nodes
        if n.key.name == "senior data engineer at northwind (line 1)"
    )

    assert role.key.kind is NodeKind.ROLE
    assert role.dates is not None and role.dates.start == date(2021, 3, 1)
    assert role.properties["title"] == "Senior Data Engineer"


def test_a_skills_line_outside_any_role_is_a_mention_by_the_document() -> None:
    mentions = _edges(_cv_graph(), Relation.MENTIONS)

    assert [(e.source.kind, e.target.name, e.cites_line) for e in mentions] == [
        (NodeKind.DOCUMENT, "kafka", 5)
    ]


def test_a_canonical_spelling_is_an_inferred_alias_that_cites_nothing() -> None:
    aliases = _edges(_cv_graph(), Relation.ALIAS_OF)

    assert [(e.source.name, e.target.name) for e in aliases] == [
        ("postgres", "postgresql")
    ]
    assert aliases[0].inferred and aliases[0].cites_line is None


def test_years_with_a_term_are_the_union_of_its_roles() -> None:
    fact = experience_with(_cv_graph(), "python", as_of=date(2026, 9, 29))

    assert fact.months == 79  # Jun 2018 – Dec 2024, both roles, no gap
    assert fact.dated_roles == 2


def test_a_canonical_spelling_reached_only_by_alias_has_no_experience() -> None:
    fact = experience_with(_cv_graph(), "postgresql", as_of=date(2026, 9, 29))

    assert fact.months == 0 and fact.dated_roles == 0


def test_a_mention_outside_a_role_adds_no_years() -> None:
    fact = experience_with(_cv_graph(), "kafka", as_of=date(2026, 9, 29))

    assert fact.months == 0 and fact.dated_roles == 0


def test_an_advert_requirement_requires_its_verified_technologies() -> None:
    requirement = AtomicRequirementProposal(
        quote="5+ years of Python and Postgres",
        statement="5+ years of Python",
        must_have=True,
        years_expected=5.0,
        seniority_expected=None,
        tech_terms=(_tech("Python"), _tech("Postgres", "postgresql"), _tech("Rust")),
    )
    plan = validate_chunk_plan(
        DocumentKind.JOB_DESCRIPTION,
        number_lines(JD),
        JD,
        [
            ProposedChunk(
                first_line=1,
                last_line=1,
                kind="requirement",
                atomic_requirements=(requirement,),
            )
        ],
    )

    graph = graph_from_chunks(plan.chunks)

    requires = {(e.target.name, e.cites_line) for e in _edges(graph, Relation.REQUIRES)}
    assert requires == {("python", 1), ("postgres", 1)}
    assert {e.source.kind for e in _edges(graph, Relation.REQUIRES)} == {
        NodeKind.REQUIREMENT
    }
    assert [
        (e.source.name, e.target.name) for e in _edges(graph, Relation.ALIAS_OF)
    ] == [("postgres", "postgresql")]


def test_inferred_edges_join_the_graph_with_the_nodes_they_name() -> None:
    graph = _cv_graph()
    edge = GraphEdge(
        _tech_key("kafka"),
        NodeKey(NodeKind.CATEGORY, "event streaming"),
        Relation.IS_A,
        None,
    )

    joined = graph.with_inferred([edge, edge])

    assert joined.edges == (*graph.edges, edge)
    added = [n.key for n in joined.nodes if n not in graph.nodes]
    assert added == [NodeKey(NodeKind.CATEGORY, "event streaming")]


def test_only_inferred_edges_can_be_joined_later() -> None:
    asserted = GraphEdge(_tech_key("a"), _tech_key("b"), Relation.USED, 1)

    with pytest.raises(ValueError, match="inferred"):
        _cv_graph().with_inferred([asserted])


@pytest.mark.parametrize(
    ("relation", "cites_line"),
    [(Relation.USED, None), (Relation.IS_A, 3)],
    ids=["asserted-without-citation", "inferred-with-citation"],
)
def test_an_edge_cites_a_chunk_exactly_when_it_is_asserted(
    relation: Relation, cites_line: int | None
) -> None:
    with pytest.raises(ValueError, match="cite"):
        GraphEdge(
            source=_tech_key("a"),
            target=_tech_key("b"),
            relation=relation,
            cites_line=cites_line,
        )
