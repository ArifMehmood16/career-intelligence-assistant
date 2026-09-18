"""Readiness probe — database, migrations and configured providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.engine import Engine

from career_assistant.adapters.persistence.engine import create_db_engine, ping_database
from career_assistant.adapters.persistence.migrate import alembic_config
from career_assistant.settings import DatabaseSettings, ProviderSettings


class ReadinessProbe(Protocol):
    @property
    def database(self) -> str: ...

    @property
    def migrations(self) -> str: ...

    @property
    def completion_provider(self) -> str: ...

    @property
    def embedding_provider(self) -> str: ...

    @property
    def hosted_egress(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class StaticReadiness:
    database: str
    migrations: str
    completion_provider: str
    embedding_provider: str
    hosted_egress: bool


def _migration_status(engine: Engine) -> str:
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    cfg = alembic_config(str(engine.url.render_as_string(hide_password=False)))
    script = ScriptDirectory.from_config(cfg)
    heads = set(script.get_heads())
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current = set(context.get_current_heads())
    if current == heads:
        return "current"
    return "pending"


class SettingsReadiness:
    """Production probe: ping Postgres, compare Alembic heads, read settings."""

    def __init__(
        self,
        database: DatabaseSettings | None = None,
        providers: ProviderSettings | None = None,
        *,
        engine: Engine | None = None,
    ) -> None:
        self._database = database or DatabaseSettings()
        self._providers = providers or ProviderSettings()
        self._engine = engine or create_db_engine(self._database)

    def check(self) -> StaticReadiness:
        try:
            ping_database(self._engine)
            database_status = "ok"
        except Exception:
            return StaticReadiness(
                database="unavailable",
                migrations="unknown",
                completion_provider=self._providers.completion_provider,
                embedding_provider=self._providers.embedding_provider,
                hosted_egress=self._providers.allow_hosted_providers,
            )
        try:
            migrations_status = _migration_status(self._engine)
        except Exception:
            migrations_status = "unknown"
        return StaticReadiness(
            database=database_status,
            migrations=migrations_status,
            completion_provider=self._providers.completion_provider,
            embedding_provider=self._providers.embedding_provider,
            hosted_egress=self._providers.allow_hosted_providers,
        )

    @property
    def database(self) -> str:
        return self.check().database

    @property
    def migrations(self) -> str:
        return self.check().migrations

    @property
    def completion_provider(self) -> str:
        return self._providers.completion_provider

    @property
    def embedding_provider(self) -> str:
        return self._providers.embedding_provider

    @property
    def hosted_egress(self) -> bool:
        return self._providers.allow_hosted_providers
