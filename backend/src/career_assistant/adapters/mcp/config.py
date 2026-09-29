"""MCP switches, read from the server's configuration file and nowhere else.

The MCP client launches this process and controls its environment, so a switch
read from the environment would be the client's decision. `MCP_ENABLED` and
`MCP_WORKSPACE_ID` are read from `config/app.env` only, and the server refuses to
start unless both are set there.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parents[5] / "config" / "app.env"
_TRUE = frozenset({"1", "true", "yes", "on"})
_QUOTES = ("'", '"')


@dataclass(frozen=True, slots=True)
class McpConfig:
    enabled: bool
    workspace_id: str | None

    @property
    def refusal(self) -> str | None:
        """Why the server will not start, or None when it may."""
        if not self.enabled:
            return (
                "The MCP server is off. Set MCP_ENABLED=true in config/app.env to "
                "turn it on; an MCP client's environment cannot."
            )
        if self.workspace_id is None:
            return (
                "Set MCP_WORKSPACE_ID in config/app.env to the workspace id to "
                "serve. `career-assistant-mcp --list-workspaces` prints them."
            )
        return None


def read_mcp_config(path: Path = CONFIG_FILE) -> McpConfig:
    values = _read_env_file(path)
    return McpConfig(
        enabled=values.get("MCP_ENABLED", "").lower() in _TRUE,
        workspace_id=_workspace_id(values.get("MCP_WORKSPACE_ID", "")),
    )


def _workspace_id(raw: str) -> str | None:
    try:
        return str(uuid.UUID(raw))
    except ValueError:
        return None


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip().removeprefix("export ").strip()] = _value(value.strip())
    return values


def _value(raw: str) -> str:
    if len(raw) >= 2 and raw[0] in _QUOTES and raw[-1] == raw[0]:
        return raw[1:-1]
    return raw.split(" #", 1)[0].strip()
