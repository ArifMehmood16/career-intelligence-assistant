"""PLAN 18.10 — the workspace pipeline version is durable and checked."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.pipeline_store import (
    SqlPipelineVersionStore,
)
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.domain.pipeline import PipelineVersion

pytestmark = pytest.mark.integration


def _store(session_factory: sessionmaker[Session]) -> SqlPipelineVersionStore:
    return SqlPipelineVersionStore(lambda: SqlUnitOfWork(session_factory))


def test_unknown_workspace_reads_v1(session_factory: sessionmaker[Session]) -> None:
    assert _store(session_factory).get(str(uuid.uuid4())) is PipelineVersion.V1


def test_v2_choice_survives_a_fresh_store(
    session_factory: sessionmaker[Session],
) -> None:
    workspace_id = str(uuid.uuid4())

    _store(session_factory).put(workspace_id, PipelineVersion.V2)

    assert _store(session_factory).get(workspace_id) is PipelineVersion.V2


def test_database_rejects_an_unknown_version(
    session_factory: sessionmaker[Session],
) -> None:
    workspace_id = str(uuid.uuid4())
    _store(session_factory).put(workspace_id, PipelineVersion.V1)

    with session_factory() as session, pytest.raises(IntegrityError):
        session.execute(
            text(
                "UPDATE career_assistant.workspaces SET pipeline_version = 'v3' "
                "WHERE id = :id"
            ),
            {"id": workspace_id},
        )
        session.flush()
