"""httpx-backed transport used outside hermetic tests."""

from __future__ import annotations

from collections.abc import Mapping

import httpx

from career_assistant.adapters.providers.http_transport import HttpResponse


class HttpxTransport:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
        timeout_seconds: float,
    ) -> HttpResponse:
        client = self._client or httpx.Client()
        try:
            response = client.request(
                method,
                url,
                headers=dict(headers or {}),
                json=json_body,
                timeout=timeout_seconds,
            )
            return HttpResponse(
                status_code=response.status_code,
                body=response.content,
                headers=dict(response.headers),
            )
        finally:
            if self._owns_client and self._client is None:
                client.close()
