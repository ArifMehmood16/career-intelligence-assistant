"""Compose SQL-backed stores for the production application entrypoint."""

from __future__ import annotations

import logging
from dataclasses import dataclass

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
from career_assistant.adapters.persistence.v2_result_reader import SqlV2ResultReader
from career_assistant.logconfig import log_event
from career_assistant.settings import DatabaseSettings, ProviderSettings

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SqlStores:
    cv: SqlCvStore
    roles: SqlRoleStore
    supporting: SqlSupportingDocumentStore
    conversations: SqlConversationStore
    provider_choices: SqlProviderSettingsStore
    v2_results: SqlV2ResultReader
    analysis_worker: SqlAnalysisWorker


def build_sql_stores(
    settings: DatabaseSettings | None = None,
    *,
    providers: ProviderSettings | None = None,
) -> SqlStores:
    """Build production stores over one engine."""
    database = settings or DatabaseSettings()
    engine = create_db_engine(database)
    session_factory = create_session_factory(engine)
    log_event(
        _log,
        "sql.engine.created",
        host=database.host_path_hostname(),
        port=database.host_path_port(),
        echo=database.db_echo,
    )

    def uow_factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    cv_store = SqlCvStore(uow_factory)
    return SqlStores(
        cv=cv_store,
        roles=SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory),
        supporting=SqlSupportingDocumentStore(
            uow_factory=uow_factory, cv_store=cv_store
        ),
        conversations=SqlConversationStore(uow_factory),
        provider_choices=SqlProviderSettingsStore(uow_factory),
        v2_results=SqlV2ResultReader(uow_factory),
        analysis_worker=SqlAnalysisWorker(
            uow_factory,
            providers=providers,
            max_concurrent=providers.analysis_max_concurrent_jobs
            if providers is not None
            else 1,
        ),
    )
