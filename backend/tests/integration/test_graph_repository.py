"""The knowledge graph in PostgreSQL (PLAN 18.5).

Asserted edges resolve to stored chunks. Inferred edges are reachable only through
related_terms, which walks at most two hops and never returns a use.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.conftest import make_document

from career_assistant.adapters.persistence.models_v2 import ChunkRow
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.domain.chunking import (
    Chunk,
    ProposedChunk,
    RoleProposal,
    TechTermProposal,
    validate_chunk_plan,
)
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.experience import experience_from
from career_assistant.domain.knowledge_graph import (
    GraphEdge,
    NodeKey,
    NodeKind,
    Relation,
    graph_from_chunks,
)
from career_assistant.domain.lines import number_lines

pytestmark = pytest.mark.integration

CV = (
    "Senior Data Engineer, Northwind, Mar 2021 – Dec 2024\n"
    "Built retrieval over Postgres and Python.\n"
    "Software Engineer, Acme, Jun 2018 – Feb 2021\n"
    "Wrote Python services.\n"
    "Skills: Kafka\n"
)


def _role(line: int, title: str, employer: str, dates: str) -> ProposedChunk:
    return ProposedChunk(
        first_line=line,
        last_line=line,
        kind="role_heading",
        role=RoleProposal(employer=employer, title=title, date_text=dates),
    )


def _chunks() -> tuple[Chunk, ...]:
    python = TechTermProposal(surface="Python", canonical="python")
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
                tech_terms=(
                    TechTermProposal(surface="Postgres", canonical="postgresql"),
                    python,
                ),
            ),
            _role(3, "Software Engineer", "Acme", "Jun 2018 – Feb 2021"),
            ProposedChunk(
                first_line=4,
                last_line=4,
                kind="experience",
                role_ref=3,
                tech_terms=(python,),
            ),
            ProposedChunk(
                first_line=5,
                last_line=5,
                kind="skills",
                tech_terms=(TechTermProposal(surface="Kafka", canonical="kafka"),),
            ),
        ],
    )
    assert plan.problems == ()
    return plan.chunks


def _store_chunks(
    session_factory: sessionmaker[Session], ws: str, doc: str, chunks: Sequence[Chunk]
) -> dict[int, str]:
    rows = [
        ChunkRow(
            workspace_id=uuid.UUID(ws),
            document_id=uuid.UUID(doc),
            first_line=c.first_line,
            last_line=c.last_line,
            start_offset=c.start_offset,
            end_offset=c.end_offset,
            kind=c.kind,
            text=c.text,
            evidence_eligible=c.evidence_eligible,
            chunker_provider="hermetic",
            chunker_model="rules-v1",
            prompt_version="chunking-v1",
        )
        for c in chunks
    ]
    with session_factory() as session:
        session.add_all(rows)
        session.commit()
    return {row.first_line: str(row.id) for row in rows}


_TAXONOMY = (
    GraphEdge(
        NodeKey(NodeKind.TECHNOLOGY, "postgresql"),
        NodeKey(NodeKind.CATEGORY, "relational database"),
        Relation.IS_A,
        None,
    ),
    GraphEdge(
        NodeKey(NodeKind.CATEGORY, "relational database"),
        NodeKey(NodeKind.CATEGORY, "database"),
        Relation.IS_A,
        None,
    ),
)


@pytest.fixture()
def stored(
    uow: SqlUnitOfWork, session_factory: sessionmaker[Session]
) -> tuple[str, str, dict[int, str]]:
    ws = str(uuid.uuid4())
    with uow:
        uow.workspaces.ensure(ws)
        cv = uow.documents.save_admitted(ws, make_document(text=CV))
        uow.commit()
    chunks = _chunks()
    ids = _store_chunks(session_factory, ws, cv.id, chunks)
    graph = graph_from_chunks(chunks).with_inferred(_TAXONOMY)
    with uow:
        uow.graph.replace_document_graph(ws, cv.id, graph)
        uow.commit()
    return ws, cv.id, ids


def test_a_term_is_used_by_each_role_citing_the_stored_chunk(
    stored: tuple[str, str, dict[int, str]], uow: SqlUnitOfWork
) -> None:
    ws, _, ids = stored
    with uow:
        uses = uow.graph.term_uses(ws, "Python")

    assert sorted((u.employer, u.chunk_id) for u in uses) == sorted(
        [("Northwind", ids[2]), ("Acme", ids[4])]
    )
    assert all(u.relation is Relation.USED for u in uses)
    fact = experience_from([u.dates for u in uses], as_of=date(2026, 9, 29))
    assert fact.months == 79


def test_a_skills_line_is_a_mention_with_no_role(
    stored: tuple[str, str, dict[int, str]], uow: SqlUnitOfWork
) -> None:
    ws, _, ids = stored
    with uow:
        uses = uow.graph.term_uses(ws, "kafka")

    assert [(u.relation, u.chunk_id, u.role_id) for u in uses] == [
        (Relation.MENTIONS, ids[5], None)
    ]


def test_a_spelling_reached_only_through_inferred_edges_has_no_use(
    stored: tuple[str, str, dict[int, str]], uow: SqlUnitOfWork
) -> None:
    ws, _, _ = stored
    with uow:
        assert uow.graph.term_uses(ws, "postgresql") == ()
        assert uow.graph.term_uses(ws, "relational database") == ()


def test_related_terms_walk_inferred_edges_at_most_two_hops(
    stored: tuple[str, str, dict[int, str]], uow: SqlUnitOfWork
) -> None:
    ws, _, _ = stored
    with uow:
        two = uow.graph.related_terms(ws, "postgres")
        one = uow.graph.related_terms(ws, "postgres", depth=1)
        from_category = uow.graph.related_terms(ws, "relational database")

    assert {(r.name, r.depth) for r in two} == {
        ("postgresql", 1),
        ("relational database", 2),
    }
    assert {r.name for r in one} == {"postgresql"}
    assert {(r.name, r.kind) for r in from_category} >= {
        ("postgresql", NodeKind.TECHNOLOGY),
        ("database", NodeKind.CATEGORY),
        ("postgres", NodeKind.TECHNOLOGY),
    }


def test_related_terms_refuse_a_walk_deeper_than_two(
    stored: tuple[str, str, dict[int, str]], uow: SqlUnitOfWork
) -> None:
    ws, _, _ = stored
    with uow, pytest.raises(ValueError, match="depth"):
        uow.graph.related_terms(ws, "postgres", depth=3)


def test_known_technologies_list_every_technology_node(
    stored: tuple[str, str, dict[int, str]], uow: SqlUnitOfWork
) -> None:
    ws, _, _ = stored
    with uow:
        known = uow.graph.known_technologies(ws)

    assert known == {"postgres", "postgresql", "python", "kafka"}


def test_saving_a_document_graph_again_replaces_it(
    stored: tuple[str, str, dict[int, str]], uow: SqlUnitOfWork
) -> None:
    ws, cv, _ = stored
    graph = graph_from_chunks(_chunks())
    with uow:
        uow.graph.replace_document_graph(ws, cv, graph)
        uow.commit()
    with uow:
        uses = uow.graph.term_uses(ws, "python")
        related = uow.graph.related_terms(ws, "postgres")

    assert len(uses) == 2
    assert {r.name for r in related} == {"postgresql"}


def test_other_workspaces_see_nothing(
    stored: tuple[str, str, dict[int, str]], uow: SqlUnitOfWork
) -> None:
    other = str(uuid.uuid4())
    with uow:
        assert uow.graph.term_uses(other, "python") == ()
        assert uow.graph.related_terms(other, "postgres") == ()
        assert uow.graph.known_technologies(other) == frozenset()


def test_an_edge_citing_a_line_with_no_stored_chunk_is_refused(
    uow: SqlUnitOfWork,
) -> None:
    ws = str(uuid.uuid4())
    with uow:
        uow.workspaces.ensure(ws)
        cv = uow.documents.save_admitted(ws, make_document(text=CV))
        uow.commit()
    with uow, pytest.raises(ValueError, match="no stored chunk"):
        uow.graph.replace_document_graph(ws, cv.id, graph_from_chunks(_chunks()))
