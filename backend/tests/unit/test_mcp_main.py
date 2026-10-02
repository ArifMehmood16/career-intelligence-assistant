"""`career-assistant-mcp` refuses to serve unless its configuration file allows it."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_assistant.adapters.mcp import main as entry


def test_it_exits_with_the_reason_when_mcp_is_off(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "app.env"
    config.write_text("MCP_ENABLED=false\n", encoding="utf-8")

    code = entry.main([], config_file=config)

    captured = capsys.readouterr()
    assert code == 2
    assert "MCP_ENABLED=true" in captured.err
    assert captured.out == "", "stdout is the protocol channel"


def test_it_exits_when_no_workspace_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "app.env"
    config.write_text("MCP_ENABLED=true\n", encoding="utf-8")

    assert entry.main([], config_file=config) == 2
    assert "MCP_WORKSPACE_ID" in capsys.readouterr().err
