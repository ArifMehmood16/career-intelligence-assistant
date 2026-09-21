"""Compose SQL-backed stores for the production application entrypoint."""

from __future__ import annotations

from career_assistant.adapters.persistence.analysis_worker import SqlAnalysisWorker
from career_assistant.adapters.persistence.conversation_store import (
    SqlConversationStore,
)
from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.engine import (
    create_db_engine,
    create_session_factory,
)
from career_assistant.adapters.persistence.provider_settings_store import (
    SqlProviderSettingsStore,
)
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.supporting_store import (
    SqlSupportingDocumentStore,
)
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.settings import DatabaseSettings, ProviderSettings


def build_sql_stores(
    settings: DatabaseSettings | None = None,
    *,
    providers: ProviderSettings | None = None,
) -> tuple[
    SqlCvStore,
    SqlRoleStore,
    SqlSupportingDocumentStore,
    SqlConversationStore,
    SqlProviderSettingsStore,
    SqlAnalysisWorker,
]:
    """Build production stores over one engine."""
    database = settings or DatabaseSettings()
    engine = create_db_engine(database)
    session_factory = create_session_factory(engine)

    def uow_factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    cv_store = SqlCvStore(uow_factory)
    role_store = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    supporting_store = SqlSupportingDocumentStore(
        uow_factory=uow_factory, cv_store=cv_store
    )
    conversation_store = SqlConversationStore(uow_factory)
    provider_choice_store = SqlProviderSettingsStore(uow_factory)
    analysis_worker = SqlAnalysisWorker(uow_factory, providers=providers)
    return (
        cv_store,
        role_store,
        supporting_store,
        conversation_store,
        provider_choice_store,
        analysis_worker,
    )
