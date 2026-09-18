"""Scripted HTTP transport for hermetic provider contract tests."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from career_assistant.adapters.providers.http_transport import HttpResponse


@dataclass
class ScriptedTransport:
    """Returns recorded fixtures; records every call for egress assertions."""

    responses: dict[str, HttpResponse]
    calls: list[tuple[str, str]] = field(default_factory=list)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
        timeout_seconds: float,
    ) -> HttpResponse:
        del headers, json_body, timeout_seconds
        self.calls.append((method, url))
        for key, response in self.responses.items():
            if key in url:
                return response
        raise AssertionError(f"no recorded response for {method} {url}")
