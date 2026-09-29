"""Years with a technology: the union of its roles' dates (ADR 013, PLAN 18.5).

An upper bound — a role counts in full if any of its chunks names the term — in
whole months, with the end month included and "present" read as the analysis's
as_of date.
"""

from __future__ import annotations

from datetime import date

from career_assistant.domain.experience import experience_from
from career_assistant.domain.recency import DateRange

AS_OF = date(2026, 9, 29)


def _range(start: tuple[int, int], end: tuple[int, int] | None) -> DateRange:
    return DateRange(start=date(*start, 1), end=None if end is None else date(*end, 1))


def test_one_closed_role_counts_its_months_including_the_last() -> None:
    fact = experience_from([_range((2021, 3), (2024, 12))], as_of=AS_OF)

    assert fact.months == 46
    assert round(fact.years, 1) == 3.8
    assert fact.is_upper_bound is True
    assert fact.last_used == date(2024, 12, 1)
    assert fact.dated_roles == 1 and fact.undated_roles == 0


def test_overlapping_roles_are_not_counted_twice() -> None:
    fact = experience_from(
        [_range((2019, 1), (2021, 12)), _range((2021, 1), (2022, 6))], as_of=AS_OF
    )

    assert fact.months == 42
    assert fact.dated_roles == 2


def test_a_gap_between_roles_is_not_counted() -> None:
    fact = experience_from(
        [_range((2018, 1), (2018, 12)), _range((2020, 1), (2020, 12))], as_of=AS_OF
    )

    assert fact.months == 24
    assert fact.last_used == date(2020, 12, 1)


def test_present_resolves_to_the_analysis_date() -> None:
    fact = experience_from([_range((2025, 10), None)], as_of=AS_OF)

    assert fact.months == 12
    assert fact.last_used == date(2026, 9, 1)
    assert fact.ongoing is True


def test_an_undated_role_is_counted_as_a_role_but_adds_no_time() -> None:
    fact = experience_from([None, _range((2022, 1), (2022, 12))], as_of=AS_OF)

    assert fact.months == 12
    assert fact.undated_roles == 1 and fact.dated_roles == 1


def test_only_undated_roles_give_no_duration() -> None:
    fact = experience_from([None], as_of=AS_OF)

    assert fact.months == 0
    assert fact.last_used is None
    assert fact.undated_roles == 1


def test_time_after_the_analysis_date_is_not_counted() -> None:
    fact = experience_from([_range((2026, 6), (2027, 12))], as_of=AS_OF)

    assert fact.months == 4
    assert fact.last_used == date(2026, 9, 1)


def test_a_range_that_ends_before_it_starts_adds_no_time() -> None:
    fact = experience_from([_range((2024, 5), (2023, 1))], as_of=AS_OF)

    assert fact.months == 0
    assert fact.dated_roles == 1
