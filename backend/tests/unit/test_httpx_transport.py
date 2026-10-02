"""A transport failure leaves the httpx transport as a provider error, never raw."""

from __future__ import annotations

import logging

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


@pytest.mark.parametrize(
    ("error_type", "phase"),
    [
        (httpx.ConnectTimeout, "connect"),
        (httpx.ReadTimeout, "read"),
        (httpx.WriteTimeout, "write"),
        (httpx.PoolTimeout, "pool"),
        (httpx.TimeoutException, "unknown"),
    ],
)
def test_timeout_logs_only_phase_and_limit(
    caplog: pytest.LogCaptureFixture,
    error_type: type[httpx.TimeoutException],
    phase: str,
) -> None:
    private = "private-document-fragment"
    transport = _failing(error_type(private))
    with caplog.at_level(logging.ERROR), pytest.raises(ProviderTransientError):
        transport.request(
            "POST",
            "https://private-endpoint.test/secret",
            headers={"Authorization": "private-credential"},
            json_body={"user": private},
            timeout_seconds=180.0,
        )

    assert "provider.transport_failed" in caplog.text
    assert "error_category=timeout" in caplog.text
    assert f"timeout_phase={phase}" in caplog.text
    assert "timeout_seconds=180.0" in caplog.text
    for hidden in (private, "private-endpoint", "private-credential"):
        assert hidden not in caplog.text


def test_connection_failure_logs_a_safe_category(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = _failing(httpx.ConnectError("private-connection-details"))
    with caplog.at_level(logging.ERROR), pytest.raises(ProviderUnavailableError):
        transport.request("GET", "http://private-endpoint.test", timeout_seconds=1)

    assert "error_category=transport_error" in caplog.text
    assert "private-connection-details" not in caplog.text
    assert "private-endpoint" not in caplog.text
