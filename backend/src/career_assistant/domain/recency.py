"""Recency and duration derived from CV dates — domain code, never the model."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from career_assistant.domain.claims import Claim

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


_YEAR_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}
_STATED_YEARS = re.compile(
    r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+years?\b",
    re.IGNORECASE,
)


def stated_years(text: str) -> int | None:
    """Year count written in a requirement, such as 'six years' or '6 years'."""
    match = _STATED_YEARS.search(text)
    if match is None:
        return None
    token = match.group(1).casefold()
    if token.isdigit():
        value = int(token)
        return value if value > 0 else None
    return _YEAR_WORDS[token]


def covered_years(claims: Sequence[Claim]) -> float | None:
    """Years of employment after overlapping periods are merged.

    Two jobs in the same years are one stretch. A single dated claim is not
    a duration judgement; callers need at least two periods before this applies.
    """
    spans: list[tuple[date, date]] = []
    for claim in claims:
        if claim.period_start is None:
            continue
        end = claim.period_end or claim.period_start
        spans.append((claim.period_start, end))
    if len(spans) < 2:
        return None
    spans.sort()
    merged: list[tuple[date, date]] = [spans[0]]
    for start, end in spans[1:]:
        current_start, current_end = merged[-1]
        if start <= current_end:
            merged[-1] = (current_start, max(current_end, end))
        else:
            merged.append((start, end))
    days = sum((end - start).days for start, end in merged)
    return days / 365.25


def derive_duration_signal(span: DateRange | None, *, as_of: date) -> str:
    if span is None:
        return "undated"
    end = span.end or as_of
    years = max(0, int(round((end - span.start).days / 365.25)))
    return f"{years}y"
