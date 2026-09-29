"""Reads a published v2 analysis back for the API, one unit of work per call."""

from __future__ import annotations

from collections.abc import Callable

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ports.search import RetrievalTrace
from career_assistant.application.ports.v2_results import V2RoleResult


class SqlV2ResultReader:
    def __init__(self, uow_factory: Callable[[], SqlUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def result(self, workspace_id: str, role_id: str) -> V2RoleResult | None:
        with self._uow_factory() as uow:
            return uow.v2.result(workspace_id, role_id)

    def traces(
        self, workspace_id: str, role_id: str, requirement_id: str
    ) -> tuple[RetrievalTrace, ...] | None:
        with self._uow_factory() as uow:
            return uow.v2.traces(workspace_id, role_id, requirement_id)
