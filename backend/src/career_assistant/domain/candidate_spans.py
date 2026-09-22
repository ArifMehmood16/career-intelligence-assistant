"""Server-owned candidate spans. The model classifies ids; it does not write text.

A line is one span. A line with more than one sentence is one span per
sentence, so two requirements on one line are not merged. The server does not
split further: a sentence that still names two requirements stays one span
until a delimiter the server can check is defined. The model cannot invent a
boundary.
"""

from __future__ import annotations

import re
import uuid

from career_assistant.domain.documents import Span

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_MARKDOWN = re.compile(r"[*_`]+")
_LEADING_MARK = re.compile(r"^[\s>#*+\-]+")
# Stable across process restarts so SQL can persist the same span id.
_SPAN_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def candidate_units(text: str) -> tuple[tuple[int, int, str], ...]:
    """Non-empty line or sentence slices of normalised text, with offsets."""
    if not text:
        return ()
    units: list[tuple[int, int, str]] = []
    lines = text.split("\n")
    cursor = 0
    last = len(lines) - 1
    for index, line in enumerate(lines):
        start = cursor
        end = start + len(line)
        cursor = end if index == last else end + 1
        if not line.strip():
            continue
        units.extend(_sentences(line, start))
    return tuple(units)


def span_id(document_id: str, start: int, end: int) -> str:
    """Deterministic UUID for a server-owned (document, offset) span."""
    return str(uuid.uuid5(_SPAN_NAMESPACE, f"{document_id}:{start}:{end}"))


def spans_for_document(document_id: str, normalised_text: str) -> tuple[Span, ...]:
    """Build persisted Span rows for every candidate unit — no model involved."""
    return tuple(
        Span(
            id=span_id(document_id, start, end),
            document_id=document_id,
            page_number=1,
            start_offset=start,
            end_offset=end,
            text=text,
        )
        for start, end, text in candidate_units(normalised_text)
    )


def is_narrative_heading(text: str) -> bool:
    """A label that only introduces the next lines, such as a trailing colon."""
    plain = _MARKDOWN.sub("", text)
    plain = _LEADING_MARK.sub("", plain).strip()
    if not plain.endswith(":"):
        return False
    return not re.search(r"[.!?]", plain[:-1])


def _sentences(line: str, line_start: int) -> tuple[tuple[int, int, str], ...]:
    parts = [part for part in _SENTENCE_BREAK.split(line) if part]
    if len(parts) <= 1:
        return ((line_start, line_start + len(line), line),)
    found: list[tuple[int, int, str]] = []
    search_from = 0
    for part in parts:
        rel = line.find(part, search_from)
        if rel < 0:
            rel = search_from
        abs_start = line_start + rel
        abs_end = abs_start + len(part)
        found.append((abs_start, abs_end, part))
        search_from = rel + len(part)
    return tuple(found)
