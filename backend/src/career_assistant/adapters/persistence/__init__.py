"""PostgreSQL persistence adapters."""

from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.engine import (
    create_db_engine,
    create_session_factory,
    ping_database,
    session_scope,
)
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.schema import APP_SCHEMA
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.adapters.persistence.wiring import build_sql_stores

__all__ = [
    "APP_SCHEMA",
    "SqlCvStore",
    "SqlRoleStore",
    "SqlUnitOfWork",
    "build_sql_stores",
    "create_db_engine",
    "create_session_factory",
    "ping_database",
    "session_scope",
]
