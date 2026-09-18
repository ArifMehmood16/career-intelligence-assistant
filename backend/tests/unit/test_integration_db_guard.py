"""Refuse equal DATABASE_URL and TEST_DATABASE_URL before any DB work."""

from __future__ import annotations

import pytest

from career_assistant.settings import DatabaseSettings


def test_integration_settings_refuse_shared_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared = "postgresql+psycopg://career:career@localhost:5432/career_assistant"
    monkeypatch.setenv("DATABASE_URL", shared)
    monkeypatch.setenv("TEST_DATABASE_URL", shared)
    with pytest.raises(Exception, match="TEST_DATABASE_URL"):
        DatabaseSettings()
