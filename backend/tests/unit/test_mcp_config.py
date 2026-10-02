"""The MCP server's switches come from its configuration file, never the client.

The MCP client launches the process and controls its environment, so a switch
read from there would be the client's decision, not the server owner's.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from career_assistant.adapters.mcp.config import read_mcp_config

WS = "7c2f7a4e-4d7a-4a51-9b8e-1f2a3b4c5d6e"


def _file(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "app.env"
    path.write_text(body, encoding="utf-8")
    return path


def test_the_server_is_off_without_a_file(tmp_path: Path) -> None:
    config = read_mcp_config(tmp_path / "missing.env")

    assert config.enabled is False
    assert config.refusal is not None
    assert "MCP_ENABLED" in config.refusal


def test_the_launching_environment_cannot_turn_it_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_ENABLED", "true")
    monkeypatch.setenv("MCP_WORKSPACE_ID", WS)

    config = read_mcp_config(_file(tmp_path, "DATABASE_URL=x\n"))

    assert (config.enabled, config.workspace_id) == (False, None)


def test_enabled_needs_a_workspace_id(tmp_path: Path) -> None:
    missing = read_mcp_config(_file(tmp_path, "MCP_ENABLED=true\n"))
    malformed = read_mcp_config(
        _file(tmp_path, "MCP_ENABLED=true\nMCP_WORKSPACE_ID=not-a-uuid\n")
    )

    assert missing.refusal is not None and "MCP_WORKSPACE_ID" in missing.refusal
    assert malformed.workspace_id is None
    assert malformed.refusal is not None


def test_a_file_that_enables_it_serves_one_workspace(tmp_path: Path) -> None:
    config = read_mcp_config(
        _file(
            tmp_path,
            "# comment\n"
            "MCP_ENABLED = true   # the owner's decision\n"
            f'MCP_WORKSPACE_ID="{WS}"\n',
        )
    )

    assert (config.enabled, config.workspace_id, config.refusal) == (True, WS, None)
