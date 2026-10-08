"""Migrate the configured database before replacing the process with the API."""

from __future__ import annotations

import logging
import os
import sys

from alembic.util import CommandError
from sqlalchemy.exc import SQLAlchemyError

from career_assistant.adapters.persistence.migrate import upgrade_head
from career_assistant.settings import DatabaseSettings

logger = logging.getLogger(__name__)


def main() -> None:
    try:
        upgrade_head(DatabaseSettings().database_url)
    except (CommandError, SQLAlchemyError, OSError, ValueError) as exc:
        logger.error("startup.migration_failed error_type=%s", type(exc).__name__)
        raise SystemExit(1) from None
    os.execv(
        sys.executable,
        (
            sys.executable,
            "-m",
            "uvicorn",
            "career_assistant.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ),
    )


if __name__ == "__main__":
    main()
