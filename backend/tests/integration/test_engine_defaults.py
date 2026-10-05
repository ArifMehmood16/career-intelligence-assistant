"""Application connections preserve float round trips despite server defaults."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from career_assistant.adapters.persistence.engine import create_db_engine
from career_assistant.settings import DatabaseSettings

pytestmark = pytest.mark.integration


def test_connections_override_reduced_float_output_precision(
    database_settings: DatabaseSettings,
) -> None:
    url = make_url(database_settings.test_database_url).update_query_dict(
        {"options": "-c extra_float_digits=0"}
    )
    engine = create_db_engine(
        database_settings, url=url.render_as_string(hide_password=False)
    )
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SHOW extra_float_digits")) == "3"
            value = 60.714285714285715
            assert (
                connection.scalar(
                    text("SELECT CAST(:value AS double precision)"), {"value": value}
                )
                == value
            )
    finally:
        engine.dispose()
