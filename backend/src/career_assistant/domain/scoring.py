"""Deterministic fit scoring — pure functions over mappings and a rubric."""

from __future__ import annotations

from dataclasses import dataclass

from career_assistant.domain.mapping import (
    MappingStatus,
)


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    requirement_id: str
    must_have: bool
    status: MappingStatus
    weight: float
    status_factor: float
    recency_factor: float
    contribution: float
    adjudicated: bool = False


@dataclass(frozen=True, slots=True)
class ScoreExplanation:
    score: float
    band: str
    components: tuple[ScoreComponent, ...]
    denominator: float
    numerator: float
    # False for unscored and for incomplete analysis. A genuine zero is True.
    publishable: bool = True
