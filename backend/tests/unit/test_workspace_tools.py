"""The tool registry over a whole workspace, for callers with no ask request."""

from __future__ import annotations

import json

from tests.support.mcp_workspace import WORKSPACE, analysed_workspace

from career_assistant.application.ask.registry import TOOL_NAMES
from career_assistant.application.ask.workspace_tools import workspace_registry


def test_the_workspace_registry_lists_its_analysed_roles() -> None:
    ws = analysed_workspace("Analytics Engineer", "Data Engineer")

    registry = workspace_registry(WORKSPACE, roles=ws.roles, cv_store=ws.cv)

    assert tuple(tool.name for tool in registry.tools) == TOOL_NAMES
    listed = json.loads(registry.call("list_roles", {}).output)["roles"]
    assert {role["roleId"] for role in listed} == set(ws.role_ids)


def test_search_finds_the_cv_text_verbatim() -> None:
    ws = analysed_workspace()

    registry = workspace_registry(WORKSPACE, roles=ws.roles, cv_store=ws.cv)
    run = registry.call("search_evidence", {"query": "Looker dashboards"})

    assert any("Built Looker dashboards" in text for _id, text in run.chunks)


def test_another_workspace_sees_nothing() -> None:
    ws = analysed_workspace()

    registry = workspace_registry(
        "00000000-0000-4000-8000-000000000000", roles=ws.roles, cv_store=ws.cv
    )

    assert json.loads(registry.call("list_roles", {}).output) == {"roles": []}
    assert registry.call("search_evidence", {"query": "dbt"}).chunks == ()
