"""Requirement extraction port — adapters extract; domain/application decide."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from career_assistant.domain.documents import DocumentKind, Span
from career_assistant.domain.requirements import Requirement


@dataclass(frozen=True, slots=True)
class RequirementExtractionResult:
    requirements: tuple[Requirement, ...]
    spans: tuple[Span, ...]


class RequirementExtractionPort(Protocol):
    def extract(
        self,
        *,
        document_id: str,
        document_kind: DocumentKind,
        normalised_text: str,
    ) -> RequirementExtractionResult: ...
