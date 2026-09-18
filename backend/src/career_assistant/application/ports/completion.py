"""Completion port — extraction and phrasing only."""

from __future__ import annotations

from typing import Protocol

from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)


class CompletionPort(Protocol):
    @property
    def capabilities(self) -> CapabilityDescriptor: ...

    def complete(self, request: CompletionRequest) -> CompletionResult: ...
