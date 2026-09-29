"""Workspace pipeline-version store — hermetic in-memory default."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from career_assistant.domain.pipeline import PipelineVersion


class PipelineVersionStore(Protocol):
    def get(self, workspace_id: str) -> PipelineVersion: ...

    def put(self, workspace_id: str, version: PipelineVersion) -> None: ...


@dataclass
class InMemoryPipelineVersionStore:
    """Process-local pipeline choices — API hermetic default only."""

    versions: dict[str, PipelineVersion] = field(default_factory=dict)

    def get(self, workspace_id: str) -> PipelineVersion:
        return self.versions.get(workspace_id, PipelineVersion.V1)

    def put(self, workspace_id: str, version: PipelineVersion) -> None:
        self.versions[workspace_id] = version
