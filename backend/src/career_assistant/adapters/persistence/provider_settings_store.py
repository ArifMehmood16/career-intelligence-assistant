"""SQL-backed workspace provider choice — production source of truth."""

from __future__ import annotations

from collections.abc import Callable

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.providers.catalogue import ProviderChoice


class SqlProviderSettingsStore:
    """ProviderChoiceStore over the provider_settings table."""

    def __init__(self, uow_factory: Callable[[], SqlUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def get(self, workspace_id: str) -> ProviderChoice | None:
        with self._uow_factory() as uow:
            return uow.provider_settings.get(workspace_id)

    def put(self, workspace_id: str, choice: ProviderChoice) -> None:
        with self._uow_factory() as uow:
            uow.workspaces.ensure(workspace_id)
            uow.provider_settings.put(workspace_id, choice)
            uow.commit()
