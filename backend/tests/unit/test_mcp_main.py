"""`career-assistant-mcp` refuses to serve unless its configuration file allows it."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from career_assistant.adapters.mcp import main as entry
from career_assistant.logconfig import configure_logging, log_event


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


def test_the_server_logs_to_stderr_and_the_configured_file_never_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log_file = tmp_path / "mcp.log"
    config = tmp_path / "app.env"
    config.write_text(f"LOG_LEVEL=INFO\nLOG_FILE={log_file}\n", encoding="utf-8")

    entry.configure_server_logging(config)
    log_event(logging.getLogger("career_assistant.adapters.mcp.server"), "tool ran")
    for handler in logging.getLogger("career_assistant").handlers:
        handler.flush()
    configure_logging(force=True)

    captured = capsys.readouterr()
    assert "tool ran" in captured.err
    assert captured.out == "", "stdout is the protocol channel"
    assert "tool ran" in log_file.read_text(encoding="utf-8")
