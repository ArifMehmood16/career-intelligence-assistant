"""`career-assistant-mcp`: serve one workspace to a local MCP client over stdio.

Off unless `config/app.env` sets MCP_ENABLED and MCP_WORKSPACE_ID. Stdout carries
the protocol, so every message for a person goes to stderr.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server

from career_assistant.adapters.mcp.config import CONFIG_FILE, read_mcp_config
from career_assistant.adapters.mcp.server import build_server
from career_assistant.adapters.persistence.cv_store import SqlCvStore
from career_assistant.adapters.persistence.engine import (
    create_db_engine,
    create_session_factory,
)
from career_assistant.adapters.persistence.role_store import SqlRoleStore
from career_assistant.adapters.persistence.supporting_store import (
    SqlSupportingDocumentStore,
)
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ask.registry import ToolRegistry
from career_assistant.application.ask.workspace_tools import workspace_registry
from career_assistant.settings import DatabaseSettings


def main(argv: Sequence[str] | None = None, *, config_file: Path = CONFIG_FILE) -> int:
    args = _parser().parse_args(argv)
    if args.list_workspaces:
        return _list_workspaces(DatabaseSettings(_env_file=config_file))
    config = read_mcp_config(config_file)
    if config.refusal is not None or config.workspace_id is None:
        print(config.refusal, file=sys.stderr)
        return 2
    server = build_server(
        _registry_factory(DatabaseSettings(_env_file=config_file), config.workspace_id)
    )
    anyio.run(_serve, server)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="career-assistant-mcp",
        description=(
            "Serve one Career Intelligence workspace, read-only, to a local MCP "
            "client over stdio. Enable it in config/app.env."
        ),
    )
    parser.add_argument(
        "--list-workspaces",
        action="store_true",
        help="print each workspace id with its role count, then exit",
    )
    return parser


def _uow_factory(database: DatabaseSettings) -> Callable[[], SqlUnitOfWork]:
    session_factory = create_session_factory(create_db_engine(database))

    def uow_factory() -> SqlUnitOfWork:
        return SqlUnitOfWork(session_factory)

    return uow_factory


def _registry_factory(
    database: DatabaseSettings, workspace_id: str
) -> Callable[[], ToolRegistry]:
    uow_factory = _uow_factory(database)
    cv = SqlCvStore(uow_factory)
    roles = SqlRoleStore(cv_store=cv, uow_factory=uow_factory)
    supporting = SqlSupportingDocumentStore(uow_factory=uow_factory, cv_store=cv)

    def registry() -> ToolRegistry:
        return workspace_registry(
            workspace_id, roles=roles, cv_store=cv, supporting_store=supporting
        )

    return registry


def _list_workspaces(database: DatabaseSettings) -> int:
    with _uow_factory(database)() as uow:
        summaries = uow.workspaces.summaries()
    if not summaries:
        print("No workspaces yet. Open the web app and upload a CV first.")
    for summary in summaries:
        cv = "CV uploaded" if summary.has_cv else "no CV"
        print(f"{summary.workspace_id}  {summary.roles} roles  {cv}")
    return 0


async def _serve(server: Server[Any]) -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )
