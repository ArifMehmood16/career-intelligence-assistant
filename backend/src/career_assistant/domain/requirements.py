"""Requirement — a job-description claim unit with a justifying source span."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ItemType(StrEnum):
    """What an extracted line of a job description actually is.

    An advert mixes what it needs, what you would do, what it pays and what the
    role explicitly is not. Scoring a candidate against a salary band is a
    category error, so the kind is extracted and only some kinds are scored.
    """

    REQUIREMENT = "requirement"
    RESPONSIBILITY = "responsibility"
    BENEFIT = "benefit"
    LOGISTICS = "logistics"
    NON_REQUIREMENT = "non_requirement"


SCOREABLE_ITEM_TYPES = frozenset({ItemType.REQUIREMENT, ItemType.RESPONSIBILITY})


@dataclass(frozen=True, slots=True)
class Requirement:
    id: str
    text: str
    competency: str
    seniority_signal: str | None
    must_have: bool
    source_span_id: str
    extraction_confidence: float
    is_vague: bool
    item_type: ItemType = ItemType.REQUIREMENT

    @property
    def is_scoreable(self) -> bool:
        return self.item_type in SCOREABLE_ITEM_TYPES

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("requirement text must be non-empty")
        if not 0.0 <= self.extraction_confidence <= 1.0:
            raise ValueError("extraction_confidence must be between 0 and 1")
