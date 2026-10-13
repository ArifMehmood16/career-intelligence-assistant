"""Role lifecycle lines name the role a human typed (spec 013)."""

from __future__ import annotations

import logging

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.support.v2_http import JD, queue_role, sql_app

pytestmark = pytest.mark.integration


def _lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records]


def test_adding_reanalysing_and_deleting_a_role_are_described(
    session_factory: sessionmaker[Session], caplog: pytest.LogCaptureFixture
) -> None:
    app = sql_app(session_factory)
    with caplog.at_level(logging.INFO, logger="career_assistant"):
        role_id, job_id = queue_role(app)
        app.client.post(f"/api/roles/{role_id}/reanalyse")
        app.client.delete(f"/api/roles/{role_id}")

    lines = _lines(caplog)
    assert (
        "Adding a role role_title=Data Engineer company=Northwind "
        f"description_characters={len(JD)}"
    ) in lines
    assert any(
        line.startswith("Role added and its analysis queued")
        and f"role_id={role_id}" in line
        and f"job_id={job_id}" in line
        for line in lines
    )
    assert any(
        line.startswith("Analysis already queued or running") and job_id in line
        for line in lines
    )
    assert any(
        line.startswith("Deleted the role role_title=Data Engineer company=Northwind")
        for line in lines
    )
