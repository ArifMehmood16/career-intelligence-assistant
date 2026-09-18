"""Hermetic tests for local database bootstrap helpers."""

from __future__ import annotations

import pytest

from career_assistant.adapters.persistence.ensure_db import (
    _quote_ident,
    database_name_from_url,
    maintenance_url_for,
)


def test_database_name_extracted_from_url() -> None:
    assert (
        database_name_from_url(
            "postgresql+psycopg://career:career@localhost:5432/career_assistant"
        )
        == "career_assistant"
    )


def test_maintenance_url_switches_to_postgres_db() -> None:
    url = "postgresql+psycopg://career:secret@localhost:5432/career_assistant"
    assert maintenance_url_for(url) == (
        "postgresql+psycopg://career:secret@localhost:5432/postgres"
    )


def test_quote_ident_rejects_unsafe_names() -> None:
    with pytest.raises(ValueError):
        _quote_ident("evil; drop database")
    assert _quote_ident("career_assistant") == '"career_assistant"'
