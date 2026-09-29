"""A citation counts only when this turn's tools returned that chunk verbatim."""

from __future__ import annotations

from collections.abc import Mapping


def citation_problems(
    citations: tuple[tuple[str, str], ...], chunks: Mapping[str, str]
) -> tuple[str, ...]:
    """Each pair is a chunk id and a quote. Problems name the id, never the quote."""
    problems: list[str] = []
    for chunk_id, quote in citations:
        text = chunks.get(chunk_id)
        if text is None:
            problems.append(f"{chunk_id}: unknown_chunk")
        elif quote not in text:
            problems.append(f"{chunk_id}: quote_not_verbatim")
    return tuple(problems)
