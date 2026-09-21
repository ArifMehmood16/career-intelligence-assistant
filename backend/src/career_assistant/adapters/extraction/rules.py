"""Deterministic rule-based requirement extraction (default / hermetic path)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from career_assistant.application.ports.extraction import RequirementExtractionResult
from career_assistant.domain.documents import DocumentKind, Span
from career_assistant.domain.requirements import Requirement

# PDF extractors emit "•Text" with no space; normalisation makes that "-Text".
_BULLET = re.compile(r"^\s*[-*•]\s*(.+)$")
_MUST_HEADERS = re.compile(
    r"^(requirements|must[- ]haves?|what you.ll need|you must have)\b",
    re.IGNORECASE,
)
_DESIRABLE_HEADERS = re.compile(
    r"^(desirable|nice to have|nice-to-have|preferred|bonus)\b",
    re.IGNORECASE,
)
_SENIORITY = re.compile(
    r"\b(senior(?:-level)?|lead|principal|staff|junior|mid[- ]?level)\b",
    re.IGNORECASE,
)
_VAGUE_MARKERS = (
    "ownership",
    "influence",
    "growth mindset",
    "rockstar",
    "ninja",
    "self-starter",
    "wear many hats",
    "scale",
    "impact",
    "initiatives",
    "outcomes end to end",
    "operates like a senior",
)
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
    ("cuda", "cuda"),
    ("ros2", "ros"),
    ("slam", "slam"),
)


@dataclass(slots=True)
class _Bullet:
    text: str
    must_have: bool
    start: int
    end: int


class RulesRequirementExtractor:
    """Parse bulleted JD sections into Requirements with exact source spans."""

    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> RequirementExtractionResult:
        if document_kind is DocumentKind.COVER_LETTER:
            raise ValueError(
                "cover_letter documents cannot contribute requirements or alter "
                "role analysis"
            )
        if document_kind is not DocumentKind.JOB_DESCRIPTION:
            raise ValueError(
                "requirements are extracted only from job_description documents"
            )

        bullets = _parse_bullets(normalised_text)
        requirements: list[Requirement] = []
        spans: list[Span] = []
        for bullet in bullets:
            span_id = str(uuid.uuid4())
            req_id = str(uuid.uuid4())
            span = Span(
                id=span_id,
                document_id=document_id,
                page_number=1,
                start_offset=bullet.start,
                end_offset=bullet.end,
                text=normalised_text[bullet.start : bullet.end],
            )
            spans.append(span)
            seniority = _seniority_signal(bullet.text)
            is_vague = _is_vague(bullet.text, seniority)
            requirements.append(
                Requirement(
                    id=req_id,
                    text=bullet.text,
                    competency=_competency(bullet.text),
                    seniority_signal=seniority,
                    must_have=bullet.must_have,
                    source_span_id=span_id,
                    extraction_confidence=0.55 if is_vague else 0.85,
                    is_vague=is_vague,
                )
            )
        return RequirementExtractionResult(
            requirements=tuple(requirements),
            spans=tuple(spans),
        )


def _parse_bullets(text: str) -> list[_Bullet]:
    must_have = True
    bullets: list[_Bullet] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        line_start = offset
        offset += len(line)

        if not stripped:
            continue
        if _DESIRABLE_HEADERS.match(stripped):
            must_have = False
            continue
        if _MUST_HEADERS.match(stripped):
            must_have = True
            continue

        match = _BULLET.match(line)
        if match is None:
            continue
        body = match.group(1).strip()
        # Locate the body inside this line for exact offsets.
        rel = line.find(body)
        start = line_start + rel
        end = start + len(body)
        bullets.append(_Bullet(text=body, must_have=must_have, start=start, end=end))
    return bullets


def _seniority_signal(text: str) -> str | None:
    match = _SENIORITY.search(text)
    if match is None:
        return None
    return match.group(1).lower()


def _is_vague(text: str, seniority: str | None) -> bool:
    lowered = text.lower()
    has_vague = any(marker in lowered for marker in _VAGUE_MARKERS)
    has_tool = any(key in lowered for key, _ in _COMPETENCY_KEYWORDS)
    if seniority and not has_tool:
        return True
    if has_vague and not has_tool:
        return True
    return False


def _competency(text: str) -> str:
    lowered = text.lower()
    for key, label in _COMPETENCY_KEYWORDS:
        if key in lowered:
            return label
    return "general"
