"""Years of experience with a term, from the dates of the roles that used it.

Domain code, never the model (ADR 013). The result is an upper bound: a role
counts in full when any of its chunks names the term.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from career_assistant.domain.recency import DateRange


@dataclass(frozen=True, slots=True)
class ExperienceFact:
    months: int
    dated_roles: int
    undated_roles: int
    last_used: date | None
    ongoing: bool
    is_upper_bound: bool = True

    @property
    def years(self) -> float:
        return self.months / 12


def experience_from(
    ranges: Sequence[DateRange | None], *, as_of: date
) -> ExperienceFact:
    """Union of the ranges in whole months, end month included, capped at as_of."""
    dated = [r for r in ranges if r is not None]
    cap = _month(as_of)
    spans = sorted(
        (start, end)
        for start, end in ((_month(r.start), _end_month(r, cap)) for r in dated)
        if start <= end
    )
    return ExperienceFact(
        months=sum(end - start + 1 for start, end in _merged(spans)),
        dated_roles=len(dated),
        undated_roles=len(ranges) - len(dated),
        last_used=_first_of(max(end for _, end in spans)) if spans else None,
        ongoing=any(r.end is None and r.start <= as_of for r in dated),
    )


def _month(day: date) -> int:
    return day.year * 12 + day.month - 1


def _end_month(span: DateRange, cap: int) -> int:
    return cap if span.end is None else min(_month(span.end), cap)


def _first_of(month: int) -> date:
    return date(month // 12, month % 12 + 1, 1)


def _merged(spans: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
