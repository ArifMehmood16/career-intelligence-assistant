"""Pure pieces of hybrid search: query shaping and rank fusion (ADR 013)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LegWeights:
    dense: float = 1.0
    lexical: float = 1.0
    exact: float = 1.0


@dataclass(frozen=True, slots=True)
class SearchHit:
    chunk_id: str
    fused_score: float
    dense_rank: int | None
    lexical_rank: int | None
    exact_rank: int | None


# After stemming these match nearly every chunk, so an OR query would rank noise.
GENERIC_REQUIREMENT_WORDS = frozenset(
    {
        "ability",
        "background",
        "demonstrable",
        "demonstrated",
        "excellent",
        "experience",
        "experienced",
        "expertise",
        "familiarity",
        "good",
        "knowledge",
        "proven",
        "skill",
        "skills",
        "solid",
        "strong",
        "understanding",
        "year",
        "years",
    }
)
_EDGE_PUNCTUATION = ",.;:()[]!?\"'"


def lexical_query_text(text: str) -> str:
    """The requirement's words for the OR-ed full-text query, generic words removed."""
    kept = [
        word
        for word in text.split()
        if word.strip(_EDGE_PUNCTUATION).casefold() not in GENERIC_REQUIREMENT_WORDS
    ]
    return " ".join(kept)


def query_terms(
    surfaces: Iterable[str], *, aliases: Iterable[str] = ()
) -> tuple[str, ...]:
    """Lowercased technology names for the exact-term leg, verified and alias."""
    names = {" ".join(t.split()).casefold() for t in (*surfaces, *aliases)}
    return tuple(sorted(name for name in names if name))


def fuse(
    *,
    dense: Sequence[str],
    lexical: Sequence[str],
    exact: Sequence[str],
    weights: LegWeights,
    rrf_k: int,
    limit: int,
) -> tuple[SearchHit, ...]:
    """Weighted reciprocal rank fusion; equal scores are ordered by chunk id."""
    ranks = [_ranks(dense), _ranks(lexical), _ranks(exact)]
    leg_weights = (weights.dense, weights.lexical, weights.exact)
    hits = [
        SearchHit(
            chunk_id=chunk_id,
            fused_score=sum(
                weight / (rrf_k + leg[chunk_id])
                for weight, leg in zip(leg_weights, ranks, strict=True)
                if chunk_id in leg
            ),
            dense_rank=ranks[0].get(chunk_id),
            lexical_rank=ranks[1].get(chunk_id),
            exact_rank=ranks[2].get(chunk_id),
        )
        for chunk_id in {*dense, *lexical, *exact}
    ]
    hits.sort(key=lambda hit: (-hit.fused_score, hit.chunk_id))
    return tuple(hits[:limit])


def _ranks(ordered: Sequence[str]) -> dict[str, int]:
    return {chunk_id: rank for rank, chunk_id in enumerate(ordered, start=1)}
