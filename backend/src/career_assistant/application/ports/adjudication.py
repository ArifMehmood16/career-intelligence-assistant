"""Adjudication port — the model tie-breaks lexical/embedding disagreements."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AdjudicationPair:
    requirement_id: str
    claim_id: str
    requirement_text: str
    claim_context: str


@dataclass(frozen=True, slots=True)
class AssessmentEvidence:
    claim_id: str
    span_ids: tuple[str, ...]
    text: str
    adjacent: bool


@dataclass(frozen=True, slots=True)
class AssessmentItem:
    requirement_id: str
    requirement_text: str
    conditions: tuple[str, ...]
    evidence: tuple[AssessmentEvidence, ...]


class AdjudicationPort(Protocol):
    def adjudicate(
        self, pairs: Sequence[AdjudicationPair]
    ) -> Mapping[tuple[str, str], bool]: ...
