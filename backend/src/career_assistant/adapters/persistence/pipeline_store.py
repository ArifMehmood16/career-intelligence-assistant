"""PipelineVersionStore over the workspaces table (PLAN 18.10)."""

from __future__ import annotations

from collections.abc import Callable

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.domain.pipeline import PipelineVersion


class SqlPipelineVersionStore:
    def __init__(self, uow_factory: Callable[[], SqlUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def get(self, workspace_id: str) -> PipelineVersion:
        with self._uow_factory() as uow:
            return uow.workspaces.pipeline_version(workspace_id)

    def put(self, workspace_id: str, version: PipelineVersion) -> None:
        with self._uow_factory() as uow:
            uow.workspaces.set_pipeline_version(workspace_id, version)
            uow.commit()
