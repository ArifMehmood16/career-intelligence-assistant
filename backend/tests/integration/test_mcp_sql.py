"""The MCP server over PostgreSQL: one workspace, read fresh on each call."""

from __future__ import annotations

from typing import Any

import anyio
import pytest
from mcp import Client
from sqlalchemy.orm import Session, sessionmaker
from tests.support.v2_http import analyse, sql_app

from career_assistant.adapters.mcp import main as entry
from career_assistant.adapters.mcp.server import build_server
from career_assistant.settings import DatabaseSettings

pytestmark = pytest.mark.integration


def _elsewhere(settings: DatabaseSettings) -> str:
    """A different name, so settings accept the test database as DATABASE_URL."""
    return settings.test_database_url + "_unused"


def test_list_workspaces_prints_each_id_and_its_roles(
    session_factory: sessionmaker[Session],
    database_settings: DatabaseSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = sql_app(session_factory)
    analyse(app)
    workspace = app.client.cookies["workspace"]
    # main() reads DATABASE_URL like the API does; point it at the test database.
    monkeypatch.setenv("DATABASE_URL", database_settings.test_database_url)
    monkeypatch.setenv("TEST_DATABASE_URL", _elsewhere(database_settings))

    assert entry.main(["--list-workspaces"]) == 0

    assert f"{workspace}  1 roles  CV uploaded" in capsys.readouterr().out


def test_an_mcp_client_reads_the_analysed_role_and_its_evidence(
    session_factory: sessionmaker[Session],
    database_settings: DatabaseSettings,
) -> None:
    app = sql_app(session_factory)
    role_id, _job = analyse(app)
    workspace = app.client.cookies["workspace"]
    registry = entry._registry_factory(
        DatabaseSettings(
            database_url=database_settings.test_database_url,
            test_database_url=_elsewhere(database_settings),
        ),
        workspace,
    )

    async def session() -> Any:
        async with Client(build_server(registry)) as client:
            roles = await client.call_tool("list_roles", {})
            found = await client.call_tool("search_evidence", {"query": "Python"})
            return roles, found

    roles, found = anyio.run(session)

    assert [r["roleId"] for r in roles.structured_content["roles"]] == [role_id]
    assert found.structured_content["chunks"], "the CV mentions Python"
    assert all(c["source"] in {"cv"} for c in found.structured_content["chunks"])
