"""Phase 4.1 — database topology and configuration contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_assistant.settings import DatabaseSettings


def test_database_settings_require_psycopg_urls() -> None:
    settings = DatabaseSettings(
        database_url="postgresql+psycopg://career:career@localhost:5432/career_assistant",
        test_database_url=(
            "postgresql+psycopg://career:career@localhost:5432/career_assistant_test"
        ),
    )
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.test_database_url.startswith("postgresql+psycopg://")


def test_database_settings_reject_sqlite_and_async_drivers() -> None:
    with pytest.raises(ValidationError):
        DatabaseSettings(
            database_url="sqlite:///tmp.db",
            test_database_url=(
                "postgresql+psycopg://career:career@localhost:5432/career_assistant_test"
            ),
        )
    with pytest.raises(ValidationError):
        DatabaseSettings(
            database_url=(
                "postgresql+asyncpg://career:career@localhost:5432/career_assistant"
            ),
            test_database_url=(
                "postgresql+psycopg://career:career@localhost:5432/career_assistant_test"
            ),
        )


def test_test_database_url_must_differ_from_database_url() -> None:
    shared = "postgresql+psycopg://career:career@localhost:5432/career_assistant"
    with pytest.raises(ValidationError, match="TEST_DATABASE_URL"):
        DatabaseSettings(database_url=shared, test_database_url=shared)


def test_host_topology_defaults_to_localhost_5432() -> None:
    settings = DatabaseSettings(
        database_url="postgresql+psycopg://career:career@localhost:5432/career_assistant",
        test_database_url=(
            "postgresql+psycopg://career:career@localhost:5432/career_assistant_test"
        ),
    )
    assert settings.host_path_port() == 5432
    assert settings.host_path_hostname() == "localhost"


def test_compose_topology_uses_db_hostname_on_5432() -> None:
    settings = DatabaseSettings(
        database_url="postgresql+psycopg://career:career@db:5432/career_assistant",
        test_database_url=(
            "postgresql+psycopg://career:career@localhost:5432/career_assistant_test"
        ),
    )
    assert settings.is_compose_topology()
    assert settings.host_path_hostname() == "db"
    assert settings.host_path_port() == 5432


def test_connection_safety_defaults_are_bounded() -> None:
    settings = DatabaseSettings(
        database_url="postgresql+psycopg://career:career@localhost:5432/career_assistant",
        test_database_url=(
            "postgresql+psycopg://career:career@localhost:5432/career_assistant_test"
        ),
    )
    assert settings.db_pool_size >= 1
    assert settings.db_max_overflow >= 0
    assert settings.db_pool_timeout_seconds > 0
    assert settings.db_statement_timeout_ms > 0
    assert settings.db_lock_timeout_ms > 0
    assert settings.db_echo is False
