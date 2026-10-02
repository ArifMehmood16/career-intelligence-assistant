"""Contract fixtures. The PostgreSQL rows reuse the integration database fixtures."""

from tests.integration.conftest import (  # noqa: F401 - pytest fixtures
    database_settings,
    migrated_engine,
    session_factory,
)
