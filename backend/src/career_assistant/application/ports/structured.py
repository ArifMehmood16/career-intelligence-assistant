"""Structured completion: a request names a contract; a validated object returns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from career_assistant.application.ports.types import CapabilityDescriptor


@dataclass(frozen=True, slots=True)
class StructuredRequest[T: BaseModel]:
    contract: type[T]
    system: str
    user: str
    max_output_tokens: int
    temperature: float | None = None
    seed: int | None = None


@dataclass(frozen=True, slots=True)
class StructuredResult[T: BaseModel]:
    value: T
    provider_id: str
    model_tag: str
    left_machine: bool
    attempts: int
    input_tokens: int | None
    output_tokens: int | None


class StructuredCompletionPort(Protocol):
    @property
    def capabilities(self) -> CapabilityDescriptor: ...

    def complete_structured[T: BaseModel](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]: ...
