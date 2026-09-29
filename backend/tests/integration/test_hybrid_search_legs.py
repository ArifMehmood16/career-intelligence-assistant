"""Each leg of hybrid search finds what the others miss (PLAN 18.6, ADR 013).

These depend on PostgreSQL's `english` parser and stemmer, so they are SQL-only;
the port's shared behaviour is in the contract suite.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.support.search_worlds import MODEL_KEY, ChunkSeed, SqlWorld

from career_assistant.application.ports.search import HybridQuery
from career_assistant.domain.documents import DocumentKind

pytestmark = pytest.mark.integration


@pytest.fixture()
def world(session_factory: sessionmaker[Session]) -> SqlWorld:
    return SqlWorld(session_factory)


def _search(world: SqlWorld, ws: str, text: str, **overrides: object):  # noqa: ANN202
    values: dict[str, object] = {
        "workspace_id": ws,
        "text": text,
        "embedding": (0.0, 0.0, 1.0),
        "terms": (),
        "embedding_model_key": MODEL_KEY,
    }
    values.update(overrides)
    hits = world.search.search(HybridQuery(**values))  # type: ignore[arg-type]
    return {h.chunk_id: (h.dense_rank, h.lexical_rank, h.exact_rank) for h in hits}


def test_the_dense_leg_finds_a_paraphrase_that_shares_no_words(world: SqlWorld) -> None:
    ws = world.workspace()
    cv = world.document(ws, DocumentKind.CV, active=True)
    paraphrase = world.chunk(
        cv,
        ChunkSeed("Shipped retrieval over embeddings", vector=(0.9, 0.1, 0.0)),
    )
    unrelated = world.chunk(
        cv, ChunkSeed("Organised the office party", vector=(0.0, 0.1, 0.9))
    )

    ranks = _search(world, ws, "built RAG systems", embedding=(1.0, 0.0, 0.0))

    assert ranks[paraphrase] == (1, None, None)
    assert ranks[unrelated] == (2, None, None)


def test_the_lexical_leg_matches_a_stemmed_word(world: SqlWorld) -> None:
    ws = world.workspace()
    cv = world.document(ws, DocumentKind.CV, active=True)
    plural = world.chunk(cv, ChunkSeed("Built dashboards for finance teams"))

    ranks = _search(world, ws, "Experience building a dashboard")

    assert ranks == {plural: (None, 1, None)}


def test_the_lexical_leg_reads_the_context_header(world: SqlWorld) -> None:
    ws = world.workspace()
    cv = world.document(ws, DocumentKind.CV, active=True)
    bullet = world.chunk(
        cv, ChunkSeed("Built dashboards", context="Analyst role at Northwind")
    )

    assert _search(world, ws, "Northwind") == {bullet: (None, 1, None)}


def test_the_lexical_leg_ranks_broader_coverage_first(world: SqlWorld) -> None:
    ws = world.workspace()
    cv = world.document(ws, DocumentKind.CV, active=True)
    repeated = world.chunk(cv, ChunkSeed("Python Python Python Python"))
    broad = world.chunk(cv, ChunkSeed("Python services on Kafka and AWS"))

    ranks = _search(world, ws, "Python, Kafka and AWS")

    assert ranks[broad][1] == 1 and ranks[repeated][1] == 2


def test_the_exact_leg_tells_c_sharp_from_c_plus_plus(world: SqlWorld) -> None:
    ws = world.workspace()
    cv = world.document(ws, DocumentKind.CV, active=True)
    sharp = world.chunk(cv, ChunkSeed("Wrote C# services", tech_terms=("C#",)))
    plus = world.chunk(cv, ChunkSeed("Wrote C++ services", tech_terms=("C++",)))

    ranks = _search(world, ws, "C#", terms=("c#",))

    assert ranks[sharp][2] == 1
    # The english parser reads both as the lexeme "c", so only the exact leg
    # separates them.
    assert ranks[plus][2] is None
    assert ranks[sharp][1] is not None and ranks[plus][1] is not None
