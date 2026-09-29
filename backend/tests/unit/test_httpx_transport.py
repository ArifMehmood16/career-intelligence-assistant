"""A transport failure leaves the httpx transport as a provider error, never raw."""

from __future__ import annotations

import httpx
import pytest

from career_assistant.adapters.providers.httpx_transport import HttpxTransport
from career_assistant.application.ports.errors import (
    ProviderTransientError,
    ProviderUnavailableError,
)


def _failing(error: Exception) -> HttpxTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    return HttpxTransport(httpx.Client(transport=httpx.MockTransport(handler)))


def test_a_refused_connection_is_a_provider_that_is_unavailable() -> None:
    transport = _failing(httpx.ConnectError("refused"))

    with pytest.raises(ProviderUnavailableError):
        transport.request("GET", "http://ollama.test/api/tags", timeout_seconds=1.0)


def test_a_timeout_is_transient() -> None:
    transport = _failing(httpx.ReadTimeout("slow"))

    with pytest.raises(ProviderTransientError):
        transport.request("GET", "http://ollama.test/api/tags", timeout_seconds=1.0)


def test_a_response_passes_through() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={}))
    )

    response = HttpxTransport(client).request(
        "GET", "http://ollama.test/api/tags", timeout_seconds=1.0
    )

    assert (response.status_code, response.body) == (200, b"{}")
