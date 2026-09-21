"""Requirement extraction port — adapters extract; domain/application decide."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import DocumentKind, Span
from career_assistant.domain.requirements import Requirement


@dataclass(frozen=True, slots=True)
class RequirementExtractionResult:
    requirements: tuple[Requirement, ...]
    spans: tuple[Span, ...]
    # Items the model returned whose quote does not appear in the stored text.
    dropped_unverifiable: int = 0


@dataclass(frozen=True, slots=True)
class ClaimExtractionResult:
    claims: tuple[Claim, ...]
    spans: tuple[Span, ...]
    dropped_unverifiable: int = 0


class RequirementExtractionPort(Protocol):
    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> RequirementExtractionResult: ...


class ClaimExtractionPort(Protocol):
    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> ClaimExtractionResult: ...
