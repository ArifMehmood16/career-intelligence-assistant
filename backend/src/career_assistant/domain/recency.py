"""Recency and duration derived from CV dates — domain code, never the model."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

# CV exports abbreviate as often as they spell months out.
_MONTH = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t)?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
)


def _month_number(name: str) -> int:
    return _MONTHS[name.lower()[:3]]


_RANGE = re.compile(
    rf"(?P<sm>{_MONTH})\.?\s+(?P<sy>\d{{4}})\s*[\u2013\u2014\-]\s*"
    rf"(?:(?P<present>Present|Current)|(?P<em>{_MONTH})\.?\s+(?P<ey>\d{{4}}))",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date
    end: date | None  # None means Present / ongoing


def parse_date_range(text: str) -> DateRange | None:
    match = _RANGE.search(text)
    if match is None:
        return None
    start = date(int(match.group("sy")), _month_number(match.group("sm")), 1)
    if match.group("present"):
        return DateRange(start=start, end=None)
    end = date(int(match.group("ey")), _month_number(match.group("em")), 1)
    return DateRange(start=start, end=end)


def derive_recency_signal(
    span: DateRange | None,
    *,
    as_of: date,
    recent_years: int = 2,
    mid_years: int = 5,
) -> str:
    """Classify how recent the experience ended. Undated stays undated."""
    if span is None:
        return "undated"
    end = span.end or as_of
    years_ago = max(0.0, (as_of - end).days / 365.25)
    if years_ago <= recent_years:
        return "recent"
    if years_ago <= mid_years:
        return "mid"
    return "old"


def derive_duration_signal(span: DateRange | None, *, as_of: date) -> str:
    if span is None:
        return "undated"
    end = span.end or as_of
    years = max(0, int(round((end - span.start).days / 365.25)))
    return f"{years}y"
