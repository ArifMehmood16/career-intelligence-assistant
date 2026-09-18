"""Engine and session factories with connection safety defaults."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.schema import APP_SCHEMA
from career_assistant.settings import DatabaseSettings


def create_db_engine(settings: DatabaseSettings, *, url: str | None = None) -> Engine:
    """Build a pooled engine. SQL echo never prints bound parameter values."""
    engine = create_engine(
        url or settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
        pool_pre_ping=settings.db_pool_pre_ping,
        # hide_parameters keeps document/question text out of logs if echo is forced on.
        echo=settings.db_echo,
        hide_parameters=True,
    )

    statement_timeout = settings.db_statement_timeout_ms
    lock_timeout = settings.db_lock_timeout_ms

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute("SET TIME ZONE 'UTC'")
            # Application tables are in APP_SCHEMA; public remains for extensions.
            cursor.execute(f"SET search_path TO {APP_SCHEMA}, public")
            cursor.execute(f"SET statement_timeout = {int(statement_timeout)}")
            cursor.execute(f"SET lock_timeout = {int(lock_timeout)}")
        finally:
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping_database(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        present = conn.execute(
            text(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = :schema"
            ),
            {"schema": APP_SCHEMA},
        ).scalar_one_or_none()
        if present is None:
            raise RuntimeError(
                f"application schema {APP_SCHEMA!r} is missing — run make db-migrate"
            )
