"""The MCP server exposes the registry read-only, with schemas and the notice.

Driven with the SDK's in-process client, once over the initialize handshake
(2025-11-25 clients) and once over the 2026-07-28 per-request envelope.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import anyio
import jsonschema
import pytest
from mcp import Client
from tests.support.mcp_workspace import WORKSPACE, Workspace, analysed_workspace

from career_assistant.adapters.mcp.server import INSTRUCTIONS, NOTICE, build_server
from career_assistant.application.ask.registry import TOOL_NAMES
from career_assistant.application.ask.workspace_tools import workspace_registry

MODES = pytest.mark.parametrize(
    ("mode", "version"),
    [("legacy", "2025-11-25"), ("2026-07-28", "2026-07-28")],
    ids=["handshake-2025-11-25", "modern-2026-07-28"],
)

Session = Callable[[Client, Workspace], Awaitable[Any]]


def _with_client(session: Session, *, mode: str = "2026-07-28") -> Any:
    ws = analysed_workspace()
    server = build_server(
        lambda: workspace_registry(WORKSPACE, roles=ws.roles, cv_store=ws.cv)
    )

    async def run() -> Any:
        async with Client(server, mode=mode) as client:
            return await session(client, ws)

    return anyio.run(run)


@MODES
def test_every_tool_is_listed_read_only_with_an_output_schema(
    mode: str, version: str
) -> None:
    async def session(client: Client, _ws: Workspace) -> Any:
        return client.protocol_version, (await client.list_tools()).tools

    negotiated, tools = _with_client(session, mode=mode)

    assert negotiated == version
    assert [tool.name for tool in tools] == list(TOOL_NAMES)
    for tool in tools:
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
        assert "MCP client" in (tool.description or "")
        assert tool.output_schema is not None
        notice = tool.output_schema["properties"]["leftMachine"]
        assert notice["const"] == NOTICE
        assert "leftMachine" in tool.output_schema["required"]


@MODES
def test_a_result_is_structured_matches_its_schema_and_carries_the_notice(
    mode: str, version: str
) -> None:
    async def session(client: Client, ws: Workspace) -> Any:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        return tools, await client.call_tool("list_roles", {})

    tools, result = _with_client(session, mode=mode)

    assert result.is_error is not True
    structured = result.structured_content
    assert structured is not None
    jsonschema.validate(structured, tools["list_roles"].output_schema)
    assert structured["leftMachine"] == NOTICE
    assert len(structured["roles"]) == 1
    assert json.loads(result.content[0].text) == structured


def test_search_returns_the_cv_text_verbatim() -> None:
    async def session(client: Client, _ws: Workspace) -> Any:
        return await client.call_tool("search_evidence", {"query": "dbt models"})

    result = _with_client(session)

    texts = [chunk["text"] for chunk in result.structured_content["chunks"]]
    assert any("Owned dbt models in production" in text for text in texts)


def test_an_unknown_role_and_bad_input_are_error_results() -> None:
    async def session(client: Client, _ws: Workspace) -> Any:
        missing = await client.call_tool("get_role_analysis", {"role_id": "nope"})
        invalid = await client.call_tool("search_evidence", {"k": 99})
        return missing, invalid

    missing, invalid = _with_client(session)

    assert missing.is_error is True
    assert missing.structured_content is None
    assert json.loads(missing.content[0].text) == {
        "error": "role_not_found",
        "leftMachine": NOTICE,
    }
    assert invalid.is_error is True


def test_the_server_says_who_decides_where_results_go() -> None:
    assert "MCP client" in INSTRUCTIONS
    assert "untrusted" in INSTRUCTIONS
