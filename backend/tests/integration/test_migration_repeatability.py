"""Fresh/repeated migrations resolve pgvector after it moves to extensions."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from career_assistant.adapters.persistence.migrate import downgrade_base, upgrade_head
from career_assistant.settings import DatabaseSettings

pytestmark = pytest.mark.integration


def test_migration_cycles_keep_vector_resolvable(
    database_settings: DatabaseSettings,
) -> None:
    url = database_settings.test_database_url
    downgrade_base(url)
    upgrade_head(url)
    downgrade_base(url)
    upgrade_head(url)
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT 'extensions.vector'::regtype::oid"))
                is not None
            )
            assert (
                connection.scalar(text("SELECT count(*) FROM public.alembic_version"))
                == 1
            )
    finally:
        engine.dispose()
