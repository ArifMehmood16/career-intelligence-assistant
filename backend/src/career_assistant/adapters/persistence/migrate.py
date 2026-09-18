"""Helpers to apply Alembic migrations against an explicit URL."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def alembic_config(database_url: str) -> Config:
    # migrate.py → persistence → adapters → career_assistant → src → backend
    root = Path(__file__).resolve().parents[4]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    cfg.set_main_option("script_location", str(root / "migrations"))
    return cfg


def upgrade_head(database_url: str) -> None:
    command.upgrade(alembic_config(database_url), "head")


def downgrade_base(database_url: str) -> None:
    command.downgrade(alembic_config(database_url), "base")
