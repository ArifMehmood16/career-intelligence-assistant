"""httpx-backed transport used outside hermetic tests."""

from __future__ import annotations

import logging
from collections.abc import Mapping

import httpx

from career_assistant.adapters.providers.http_transport import HttpResponse
from career_assistant.application.ports.errors import (
    ProviderTransientError,
    ProviderUnavailableError,
)
from career_assistant.logconfig import log_failure

_log = logging.getLogger(__name__)
_TIMEOUT_PHASES = (
    (httpx.ConnectTimeout, "connect"),
    (httpx.ReadTimeout, "read"),
    (httpx.WriteTimeout, "write"),
    (httpx.PoolTimeout, "pool"),
)


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
        except httpx.TimeoutException as exc:
            log_failure(
                _log,
                "provider.transport_failed",
                error_category="timeout",
                timeout_phase=_timeout_phase(exc),
                timeout_seconds=timeout_seconds,
            )
            raise ProviderTransientError("provider request timed out") from exc
        except httpx.TransportError as exc:
            log_failure(
                _log,
                "provider.transport_failed",
                error_category="transport_error",
                timeout_seconds=timeout_seconds,
            )
            raise ProviderUnavailableError("provider could not be reached") from exc
        finally:
            if self._owns_client and self._client is None:
                client.close()


def _timeout_phase(error: httpx.TimeoutException) -> str:
    for error_type, phase in _TIMEOUT_PHASES:
        if isinstance(error, error_type):
            return phase
    return "unknown"
