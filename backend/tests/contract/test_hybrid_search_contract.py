"""Every HybridSearchPort passes this suite: the in-memory fake and PostgreSQL.

The PostgreSQL row runs with `-m integration`. Leg behaviour that depends on the
PostgreSQL parser (stemming, `C#`) is pinned in the SQL-only integration tests.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from tests.support.search_worlds import (
    MODEL_KEY,
    ChunkSeed,
    InMemoryWorld,
    SearchWorld,
    SqlWorld,
)

from career_assistant.application.ports.search import HybridQuery
from career_assistant.domain.documents import DocumentKind

WORLDS: dict[str, Callable[[pytest.FixtureRequest], SearchWorld]] = {
    "in-memory": lambda _request: InMemoryWorld(),
    "postgresql": lambda request: SqlWorld(request.getfixturevalue("session_factory")),
}


@pytest.fixture(
    params=[
        pytest.param("in-memory"),
        pytest.param("postgresql", marks=pytest.mark.integration),
    ]
)
def world(request: pytest.FixtureRequest) -> SearchWorld:
    return WORLDS[request.param](request)


def _query(ws: str, text: str = "", **overrides: object) -> HybridQuery:
    values: dict[str, object] = {
        "workspace_id": ws,
        "text": text,
        "embedding": (1.0, 0.0, 0.0),
        "terms": (),
        "embedding_model_key": MODEL_KEY,
    }
    values.update(overrides)
    return HybridQuery(**values)  # type: ignore[arg-type]


def _cv(world: SearchWorld, ws: str, *, active: bool = True) -> str:
    return world.document(ws, DocumentKind.CV, active=active)


def test_each_leg_reports_the_rank_it_found_a_chunk_at(world: SearchWorld) -> None:
    ws = world.workspace()
    cv = _cv(world, ws)
    dense = world.chunk(cv, ChunkSeed("Shipped retrieval", vector=(1.0, 0.0, 0.0)))
    lexical = world.chunk(cv, ChunkSeed("Built dashboards for finance"))
    exact = world.chunk(cv, ChunkSeed("Wrote services", tech_terms=("kafka",)))

    hits = world.search.search(
        _query(ws, "dashboards", terms=("kafka",), embedding=(1.0, 0.0, 0.0))
    )

    ranks = {h.chunk_id: (h.dense_rank, h.lexical_rank, h.exact_rank) for h in hits}
    assert ranks == {
        dense: (1, None, None),
        lexical: (None, 1, None),
        exact: (None, None, 1),
    }
    assert [h.chunk_id for h in hits] == sorted(ranks)
    assert all(h.fused_score == pytest.approx(1 / 61) for h in hits)


def test_a_chunk_found_by_more_legs_ranks_higher(world: SearchWorld) -> None:
    ws = world.workspace()
    cv = _cv(world, ws)
    one = world.chunk(cv, ChunkSeed("Built dashboards"))
    both = world.chunk(
        cv, ChunkSeed("Built dashboards in Kafka", tech_terms=("kafka",))
    )

    hits = world.search.search(_query(ws, "dashboards", terms=("kafka",)))

    assert [h.chunk_id for h in hits][:2] == [both, one]


def test_only_this_workspaces_evidence_chunks_are_searched(world: SearchWorld) -> None:
    ws, other = world.workspace(), world.workspace()
    cv = _cv(world, ws)
    kept = world.chunk(cv, ChunkSeed("Kafka pipelines", tech_terms=("kafka",)))
    world.chunk(
        cv, ChunkSeed("Kafka enthusiast", kind="summary", tech_terms=("kafka",))
    )
    world.chunk(cv, ChunkSeed("kafka@example.com", kind="contact"))
    world.chunk(_cv(world, other), ChunkSeed("Kafka pipelines", tech_terms=("kafka",)))

    hits = world.search.search(_query(ws, "Kafka pipelines", terms=("kafka",)))

    assert [h.chunk_id for h in hits] == [kept]


def test_an_inactive_cv_is_not_searched(world: SearchWorld) -> None:
    ws = world.workspace()
    world.chunk(_cv(world, ws, active=False), ChunkSeed("Kafka", tech_terms=("kafka",)))
    active = world.chunk(_cv(world, ws), ChunkSeed("Kafka", tech_terms=("kafka",)))

    hits = world.search.search(_query(ws, "Kafka", terms=("kafka",)))

    assert [h.chunk_id for h in hits] == [active]


def test_cover_letter_experience_is_searched_unless_excluded(
    world: SearchWorld,
) -> None:
    ws = world.workspace()
    letter = world.document(ws, DocumentKind.COVER_LETTER, active=False)
    from_letter = world.chunk(letter, ChunkSeed("I ran Kafka", tech_terms=("kafka",)))
    world.chunk(
        letter,
        ChunkSeed("I hope to learn Kafka", kind="aspiration", tech_terms=("kafka",)),
    )

    default = world.search.search(_query(ws, "Kafka", terms=("kafka",)))
    cv_only = world.search.search(
        _query(ws, "Kafka", terms=("kafka",), sources=(DocumentKind.CV,))
    )

    assert [h.chunk_id for h in default] == [from_letter]
    assert cv_only == ()


def test_a_job_description_is_never_evidence(world: SearchWorld) -> None:
    ws = world.workspace()
    advert = world.document(ws, DocumentKind.JOB_DESCRIPTION, active=False)
    world.chunk(advert, ChunkSeed("Kafka", kind="experience", tech_terms=("kafka",)))

    assert world.search.search(_query(ws, "Kafka", terms=("kafka",))) == ()


def test_the_match_count_limits_results_and_ties_follow_chunk_id(
    world: SearchWorld,
) -> None:
    ws = world.workspace()
    cv = _cv(world, ws)
    ids = [world.chunk(cv, ChunkSeed("Kafka", tech_terms=("kafka",))) for _ in range(4)]

    hits = world.search.search(_query(ws, "", terms=("kafka",), match_count=2))

    assert [h.chunk_id for h in hits] == sorted(ids)[:2]
    assert [h.exact_rank for h in hits] == [1, 2]


def test_generic_requirement_words_alone_find_nothing(world: SearchWorld) -> None:
    ws = world.workspace()
    world.chunk(_cv(world, ws), ChunkSeed("Strong experience and knowledge"))

    assert world.search.search(_query(ws, "Strong experience, knowledge")) == ()
