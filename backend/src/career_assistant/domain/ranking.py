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
        tied = end - index > 1
        for role in ordered[index:end]:
            out.append(
                RankedRole(
                    id=role.id,
                    title=role.title,
                    fit_score=role.fit_score,
                    because=role.because,
                    rank=rank,
                    tied=tied,
                )
            )
        index = end
    return tuple(out)
