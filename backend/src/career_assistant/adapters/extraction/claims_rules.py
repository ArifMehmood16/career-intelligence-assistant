"""Deterministic rule-based claim extraction from CV experience bullets."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date

from career_assistant.application.ports.extraction import ClaimExtractionResult
from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import DocumentKind, Span
from career_assistant.domain.recency import (
    DateRange,
    derive_duration_signal,
    derive_recency_signal,
    parse_date_range,
)

# PDF extractors emit "•Text" with no space; normalisation makes that "-Text".
_BULLET = re.compile(r"^\s*[-*•]\s*(.+)$")
_EXPERIENCE_HEADER = re.compile(r"^experience\b", re.IGNORECASE)
_SECTION_STOP = re.compile(r"^(skills|education|summary|projects)\b", re.IGNORECASE)
# A heading is short and is not a sentence. A wrapped body line such as
# "education customers. Live in production for two years." is neither.
_MAX_HEADING_CHARS = 40
_ROLE_HEADER = re.compile(r".+\s[—\-–]\s.+")
_COMPETENCY_KEYWORDS = (
    ("dbt", "dbt"),
    ("snowflake", "sql"),
    ("bigquery", "sql"),
    ("sql", "sql"),
    ("python", "python"),
    ("airflow", "airflow"),
    ("spark", "spark"),
    ("hadoop", "hadoop"),
    ("looker", "bi"),
    ("tableau", "bi"),
    ("power bi", "bi"),
    ("mapreduce", "hadoop"),
)


@dataclass(slots=True)
class _Role:
    date_range: DateRange | None
    date_span: Span | None


class RulesClaimExtractor:
    """Parse EXPERIENCE bullets into Claims; recency/duration from role dates."""

    def __init__(self, *, as_of: date | None = None) -> None:
        self._as_of = as_of or date.today()

    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> ClaimExtractionResult:
        if document_kind not in {DocumentKind.CV, DocumentKind.COVER_LETTER}:
            raise ValueError("claims are extracted only from the active CV document")
        self_authored = document_kind is DocumentKind.COVER_LETTER

        claims: list[Claim] = []
        spans: list[Span] = []
        # Cover letters have no EXPERIENCE heading; read bullets from the start.
        in_experience = self_authored
        current = _Role(date_range=None, date_span=None)
        offset = 0

        for line in normalised_text.splitlines(keepends=True):
            stripped = line.strip()
            line_start = offset
            offset += len(line)

            if not stripped:
                continue
            if _EXPERIENCE_HEADER.match(stripped):
                in_experience = True
                current = _Role(date_range=None, date_span=None)
                continue
            if in_experience and _is_section_heading(stripped):
                in_experience = False
                continue
            if not in_experience:
                continue

            date_range = parse_date_range(stripped)
            if date_range is not None and not _BULLET.match(line):
                date_span = _span_for(
                    document_id, normalised_text, line_start, stripped
                )
                spans.append(date_span)
                current = _Role(date_range=date_range, date_span=date_span)
                continue

            if _ROLE_HEADER.match(stripped) and not _BULLET.match(line):
                # New role header without clearing dates until a date line arrives.
                current = _Role(date_range=None, date_span=None)
                continue

            match = _BULLET.match(line)
            if match is None:
                continue
            body = match.group(1).strip()
            bullet_span = _span_for(document_id, normalised_text, line_start, body)
            spans.append(bullet_span)
            span_ids = [bullet_span.id]
            if current.date_span is not None:
                span_ids.append(current.date_span.id)
            claims.append(
                Claim(
                    id=str(uuid.uuid4()),
                    competency=_competency(body),
                    context=body,
                    duration_signal=derive_duration_signal(
                        current.date_range, as_of=self._as_of
                    ),
                    recency_signal=derive_recency_signal(
                        current.date_range, as_of=self._as_of
                    ),
                    source_span_ids=tuple(span_ids),
                    extraction_confidence=0.85,
                    period_start=(
                        current.date_range.start
                        if current.date_range is not None
                        else None
                    ),
                    period_end=(
                        current.date_range.end
                        if current.date_range is not None
                        else None
                    ),
                    self_authored=self_authored,
                )
            )

        return ClaimExtractionResult(claims=tuple(claims), spans=tuple(spans))


def _is_section_heading(stripped: str) -> bool:
    if _SECTION_STOP.match(stripped) is None:
        return False
    return len(stripped) <= _MAX_HEADING_CHARS and not stripped.endswith(".")


def _span_for(document_id: str, full_text: str, line_start: int, body: str) -> Span:
    rel = full_text.find(body, line_start)
    if rel < 0:
        rel = line_start
    start = rel
    end = start + len(body)
    return Span(
        id=str(uuid.uuid4()),
        document_id=document_id,
        page_number=1,
        start_offset=start,
        end_offset=end,
        text=full_text[start:end],
    )


def _competency(text: str) -> str:
    lowered = text.lower()
    for key, label in _COMPETENCY_KEYWORDS:
        if key in lowered:
            return label
    return "general"
