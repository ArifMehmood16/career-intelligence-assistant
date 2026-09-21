"""SQL-backed call accountant — identifiers and counts only."""

from __future__ import annotations

from collections.abc import Callable

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ports.types import CallRecord
from career_assistant.application.providers.accounting import CallAccountant


class SqlCallAccountant(CallAccountant):
    def __init__(self, uow_factory: Callable[[], SqlUnitOfWork]) -> None:
        super().__init__()
        self._uow_factory = uow_factory

    def record(self, entry: CallRecord) -> None:
        super().record(entry)
        workspace_id = entry.metadata.get("workspace_id")
        if not workspace_id:
            return
        with self._uow_factory() as uow:
            uow.workspaces.ensure(workspace_id)
            uow.accounting.insert(workspace_id, entry)
            uow.commit()
