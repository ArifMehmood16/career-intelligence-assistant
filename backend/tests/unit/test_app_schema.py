"""Application tables must not live in the public schema."""

from __future__ import annotations

from career_assistant.adapters.persistence.models import Base, DocumentRow
from career_assistant.adapters.persistence.schema import APP_SCHEMA


def test_metadata_targets_dedicated_schema() -> None:
    assert Base.metadata.schema == APP_SCHEMA
    assert APP_SCHEMA == "career_assistant"
    assert DocumentRow.__table__.schema == APP_SCHEMA
