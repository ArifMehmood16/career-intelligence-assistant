"""Pointer rules when a role analysis fails after a version bump."""

from __future__ import annotations

from career_assistant.domain.jobs import RoleStatus


def resolve_failed_analysis_pointer(
    *,
    current_version: int,
    published_versions: tuple[int, ...],
) -> tuple[int, RoleStatus]:
    """Keep a previously published analysis visible after a failed attempt.

    Reanalyse bumps ``analysis_version`` before the job runs. If the new version
    fails, its partial rows are discarded. When an earlier version still has a
    published score, the role pointer returns to that version and the role is
    ready again. A first analysis with no prior score stays failed on the
    empty version.
    """
    priors = [version for version in published_versions if version < current_version]
    if not priors:
        return current_version, RoleStatus.FAILED
    return max(priors), RoleStatus.READY
