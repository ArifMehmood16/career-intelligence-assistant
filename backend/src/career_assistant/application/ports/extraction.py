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
    # Items the model returned that are not one classification of a server span.
    dropped_unverifiable: int = 0
    # False when any server span lacks exactly one accepted classification.
    # A partial response is not a complete extraction.
    complete: bool = True


@dataclass(frozen=True, slots=True)
class ClaimExtractionResult:
    claims: tuple[Claim, ...]
    spans: tuple[Span, ...]
    dropped_unverifiable: int = 0
    complete: bool = True
    spans_supplied: int = 0
    claims_returned: int = 0
    claims_accepted: int = 0
    claims_rejected: int = 0
    roles_detected: int = 0
    roles_without_claims: int = 0


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
