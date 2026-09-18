"""Compose SQL-backed stores for the production application entrypoint."""

from __future__ import annotations

from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.engine import (
    create_db_engine,
    create_session_factory,
)
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.settings import DatabaseSettings


def build_sql_stores(
    settings: DatabaseSettings | None = None,
) -> tuple[SqlCvStore, SqlRoleStore]:
    """Build CvStore + RoleStore over one engine and session factory."""
    database = settings or DatabaseSettings()
    engine = create_db_engine(database)
    session_factory = create_session_factory(engine)

    def uow_factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    cv_store = SqlCvStore(uow_factory)
    role_store = SqlRoleStore(cv_store=cv_store, uow_factory=uow_factory)
    return cv_store, role_store
