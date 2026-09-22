"""Workspace ranking — competition ranks from stored scores, no model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RankableRole:
    id: str
    title: str
    fit_score: int
    because: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RankedRole:
    id: str
    title: str
    fit_score: int
    because: tuple[str, ...]
    rank: int
    tied: bool


def rank_roles(
    roles: tuple[RankableRole, ...] | list[RankableRole],
) -> tuple[RankedRole, ...]:
    """Order by score, then title, then id. Equal scores share a 1224 rank."""
    ordered = sorted(roles, key=lambda role: (-role.fit_score, role.title, role.id))
    out: list[RankedRole] = []
    index = 0
    while index < len(ordered):
        score = ordered[index].fit_score
        end = index + 1
        while end < len(ordered) and ordered[end].fit_score == score:
            end += 1
        rank = index + 1
        group = ordered[index:end]
        tied = len(group) > 1
        reasons = _tie_reasons(group) if tied else None
        for role in group:
            out.append(
                RankedRole(
                    id=role.id,
                    title=role.title,
                    fit_score=role.fit_score,
                    because=reasons[role.id] if reasons is not None else role.because,
                    rank=rank,
                    tied=tied,
                )
            )
        index = end
    return tuple(out)


def _tie_reasons(group: list[RankableRole]) -> dict[str, tuple[str, ...]]:
    """Name the requirements that are not on every tied role."""
    shared = set(group[0].because)
    for role in group[1:]:
        shared &= set(role.because)
    named: dict[str, tuple[str, ...]] = {}
    for role in group:
        different = tuple(item for item in role.because if item not in shared)
        named[role.id] = different or role.because
    return named
