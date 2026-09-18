"""Recency and duration derived from CV dates — domain code, never the model."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

_RANGE = re.compile(
    r"(?P<sm>January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(?P<sy>\d{4})\s*[–\-]\s*"
    r"(?:(?P<present>Present)|(?P<em>January|February|March|April|May|June|"
    r"July|August|September|October|November|December)\s+(?P<ey>\d{4}))",
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
    start = date(int(match.group("sy")), _MONTHS[match.group("sm").lower()], 1)
    if match.group("present"):
        return DateRange(start=start, end=None)
    end = date(int(match.group("ey")), _MONTHS[match.group("em").lower()], 1)
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
