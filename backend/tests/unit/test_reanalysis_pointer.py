"""PLAN 13D.6e — a failed reanalysis must not hide the previous valid score."""

from __future__ import annotations

from career_assistant.domain.jobs import RoleStatus
from career_assistant.domain.reanalysis import resolve_failed_analysis_pointer


def test_first_failed_analysis_stays_on_the_empty_version() -> None:
    version, status = resolve_failed_analysis_pointer(
        current_version=1,
        published_versions=(),
    )
    assert version == 1
    assert status is RoleStatus.FAILED


def test_failed_reanalysis_restores_the_previous_published_version() -> None:
    version, status = resolve_failed_analysis_pointer(
        current_version=2,
        published_versions=(1,),
    )
    assert version == 1
    assert status is RoleStatus.READY


def test_failed_reanalysis_picks_the_latest_prior_published_version() -> None:
    version, status = resolve_failed_analysis_pointer(
        current_version=4,
        published_versions=(1, 3),
    )
    assert version == 3
    assert status is RoleStatus.READY


def test_a_failed_attempt_with_no_prior_score_stays_failed() -> None:
    version, status = resolve_failed_analysis_pointer(
        current_version=2,
        published_versions=(2,),
    )
    assert version == 2
    assert status is RoleStatus.FAILED
