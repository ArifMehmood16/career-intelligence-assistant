"""Create missing local databases named by DATABASE_URL / TEST_DATABASE_URL."""

from __future__ import annotations

import psycopg
from sqlalchemy.engine import make_url

from career_assistant.settings import DatabaseSettings

# Maintenance DB used only to issue CREATE DATABASE. Never the app schema target.
_MAINTENANCE_DB = "postgres"


def database_name_from_url(url: str) -> str:
    parsed = make_url(url)
    if not parsed.database:
        raise ValueError("database URL must include a database name")
    return parsed.database


def maintenance_url_for(url: str) -> str:
    """Same credentials/host as ``url``, but connected to the postgres DB."""
    parsed = make_url(url)
    return parsed.set(database=_MAINTENANCE_DB).render_as_string(hide_password=False)


def _quote_ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"refusing unsafe database name: {name!r}")
    return '"' + name.replace('"', '""') + '"'


def ensure_database_exists(url: str) -> bool:
    """Create the database named in ``url`` if missing. Returns True if created."""
    name = database_name_from_url(url)
    admin_url = maintenance_url_for(url)
    # psycopg wants postgresql:// not postgresql+psycopg://
    dsn = admin_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(dsn, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (name,),
        ).fetchone()
        if exists is not None:
            return False
        conn.execute(f"CREATE DATABASE {_quote_ident(name)}")
        return True


def ensure_configured_databases(settings: DatabaseSettings) -> tuple[str, ...]:
    """Ensure DATABASE_URL and TEST_DATABASE_URL databases exist.

    Does not create roles or the application schema — Alembic owns the schema.
    The role in each URL must already exist and hold CREATEDB (or be a superuser).
    """
    created: list[str] = []
    for label, url in (
        ("DATABASE_URL", settings.database_url),
        ("TEST_DATABASE_URL", settings.test_database_url),
    ):
        name = database_name_from_url(url)
        if ensure_database_exists(url):
            created.append(f"{label}={name}")
    return tuple(created)


def main() -> None:
    settings = DatabaseSettings()
    created = ensure_configured_databases(settings)
    if created:
        print("created:", ", ".join(created))
    else:
        print(
            "databases already present:",
            database_name_from_url(settings.database_url),
            database_name_from_url(settings.test_database_url),
        )


if __name__ == "__main__":
    main()
