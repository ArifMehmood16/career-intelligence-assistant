"""Workspace provider-choice store — hermetic in-memory default."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from career_assistant.application.providers.catalogue import ProviderChoice


class ProviderChoiceStore(Protocol):
    def get(self, workspace_id: str) -> ProviderChoice | None: ...

    def put(self, workspace_id: str, choice: ProviderChoice) -> None: ...


@dataclass
class InMemoryProviderChoiceStore:
    """Process-local provider choices — API hermetic default only."""

    choices: dict[str, ProviderChoice] = field(default_factory=dict)

    def get(self, workspace_id: str) -> ProviderChoice | None:
        return self.choices.get(workspace_id)

    def put(self, workspace_id: str, choice: ProviderChoice) -> None:
        self.choices[workspace_id] = choice
