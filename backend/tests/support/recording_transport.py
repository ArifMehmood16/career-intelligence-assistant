"""A transport that returns one recorded response and keeps every request."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from career_assistant.adapters.providers.http_transport import HttpResponse


@dataclass
class RecordedRequest:
    url: str
    body: Mapping[str, Any]


@dataclass
class RecordingTransport:
    payload: Mapping[str, Any]
    requests: list[RecordedRequest] = field(default_factory=list)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
        timeout_seconds: float,
    ) -> HttpResponse:
        del method, headers, timeout_seconds
        self.requests.append(RecordedRequest(url=url, body=dict(json_body or {})))
        return HttpResponse(200, json.dumps(self.payload).encode(), {})

    @property
    def last(self) -> RecordedRequest:
        return self.requests[-1]
