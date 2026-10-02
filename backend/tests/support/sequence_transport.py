"""A transport with an ordered sequence of recorded responses or safe failures."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from career_assistant.adapters.providers.http_transport import HttpResponse
from career_assistant.application.ports.errors import ProviderError


@dataclass
class SequenceTransport:
    responses: list[HttpResponse | ProviderError]
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
        response = self.responses.pop(0)
        if isinstance(response, ProviderError):
            raise response
        return response
