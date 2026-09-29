"""Pure pieces of hybrid search (ADR 013, PLAN 18.6).

The lexical query drops generic requirement words; query terms are lowercased
technology names; reciprocal rank fusion sums weight / (k + rank) over the legs
that found a chunk, with ties broken on chunk id.
"""

from __future__ import annotations

import pytest

from career_assistant.domain.search import (
    LegWeights,
    fuse,
    lexical_query_text,
    query_terms,
)


def test_generic_requirement_words_are_removed_from_the_lexical_query() -> None:
    text = "Strong experience with 5+ years of Python and a proven ability to lead"

    assert lexical_query_text(text) == "with 5+ of Python and a to lead"


def test_a_query_of_only_generic_words_is_empty() -> None:
    assert lexical_query_text("Strong knowledge and experience") == "and"
    assert lexical_query_text("Experience, knowledge") == ""


def test_query_terms_are_lowercased_deduplicated_and_sorted() -> None:
    assert query_terms(["PostgreSQL", "C#"], aliases=["postgres", "postgresql"]) == (
        "c#",
        "postgres",
        "postgresql",
    )


def test_fusion_sums_each_leg_that_found_a_chunk() -> None:
    hits = fuse(
        dense=["a", "b"],
        lexical=["b"],
        exact=[],
        weights=LegWeights(),
        rrf_k=60,
        limit=8,
    )

    assert [h.chunk_id for h in hits] == ["b", "a"]
    assert hits[0].fused_score == pytest.approx(1 / 62 + 1 / 61)
    assert (hits[0].dense_rank, hits[0].lexical_rank, hits[0].exact_rank) == (
        2,
        1,
        None,
    )
    assert hits[1].fused_score == pytest.approx(1 / 61)


def test_leg_weights_scale_their_contribution() -> None:
    hits = fuse(
        dense=["a"],
        lexical=[],
        exact=["b"],
        weights=LegWeights(dense=1.0, lexical=1.0, exact=2.0),
        rrf_k=60,
        limit=8,
    )

    assert [h.chunk_id for h in hits] == ["b", "a"]
    assert hits[0].fused_score == pytest.approx(2 / 61)


def test_equal_scores_are_ordered_by_chunk_id_and_the_limit_applies() -> None:
    hits = fuse(
        dense=["c"],
        lexical=["a"],
        exact=["b"],
        weights=LegWeights(),
        rrf_k=60,
        limit=2,
    )

    assert [h.chunk_id for h in hits] == ["a", "b"]
