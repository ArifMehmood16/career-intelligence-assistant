"""Drop extracted artefacts whose source spans do not resolve to stored text."""

from __future__ import annotations

from career_assistant.application.intake.resolve_span import (
    SpanNotFoundError,
    resolve_span,
)
from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import Page, Span
from career_assistant.domain.requirements import Requirement


def validate_requirements_against_pages(
    requirements: tuple[Requirement, ...] | list[Requirement],
    spans: tuple[Span, ...] | list[Span],
    *,
    pages: tuple[Page, ...] | list[Page],
) -> tuple[tuple[Requirement, ...], int]:
    """Return (kept, dropped_count). Invalid span refs are dropped, never guessed."""
    by_id = {span.id: span for span in spans}
    kept: list[Requirement] = []
    dropped = 0
    for requirement in requirements:
        span = by_id.get(requirement.source_span_id)
        if span is None:
            dropped += 1
            continue
        try:
            resolve_span(span, pages)
        except SpanNotFoundError:
            dropped += 1
            continue
        kept.append(requirement)
    return tuple(kept), dropped


def validate_claims_against_pages(
    claims: tuple[Claim, ...] | list[Claim],
    spans: tuple[Span, ...] | list[Span],
    *,
    pages: tuple[Page, ...] | list[Page],
) -> tuple[tuple[Claim, ...], int]:
    """Return (kept, dropped_count). Every cited span must resolve."""
    by_id = {span.id: span for span in spans}
    kept: list[Claim] = []
    dropped = 0
    for claim in claims:
        ok = True
        for span_id in claim.source_span_ids:
            span = by_id.get(span_id)
            if span is None:
                ok = False
                break
            try:
                resolve_span(span, pages)
            except SpanNotFoundError:
                ok = False
                break
        if ok:
            kept.append(claim)
        else:
            dropped += 1
    return tuple(kept), dropped
