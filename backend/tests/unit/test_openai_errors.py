"""OpenAI rejection diagnostics identify the failure without retaining content."""

from __future__ import annotations

import json
import logging
from typing import TypedDict

import pytest
from tests.support.sequence_transport import SequenceTransport

from career_assistant.adapters.providers.http_transport import HttpResponse
from career_assistant.adapters.providers.openai.completion import (
    OpenAICompletionAdapter,
)
from career_assistant.adapters.providers.openai.embedding import OpenAIEmbeddingAdapter
from career_assistant.adapters.providers.openai.errors import classify_openai_response
from career_assistant.adapters.providers.resilience import ResiliencePolicy
from career_assistant.adapters.providers.tool_calling import OpenAIToolCaller
from career_assistant.application.ports.errors import (
    ProviderTransientError,
    ProviderUnavailableError,
)
from career_assistant.application.ports.tool_calling import (
    ChatMessage,
    ToolCallingRequest,
)
from career_assistant.application.ports.types import CompletionRequest, EmbeddingRequest


class _AdapterOptions(TypedDict):
    api_key: str
    model_tag: str
    transport: SequenceTransport
    resilience: ResiliencePolicy


def _error_response(status: int, error: object) -> HttpResponse:
    return HttpResponse(status, json.dumps({"error": error}).encode(), {})


@pytest.mark.parametrize(
    ("status", "code", "parameter", "category", "exception"),
    [
        (
            400,
            "invalid_json_schema",
            "response_format",
            "invalid_schema",
            ProviderUnavailableError,
        ),
        (
            400,
            None,
            "response_format",
            "request_format_rejected",
            ProviderUnavailableError,
        ),
        (
            400,
            "unsupported_parameter",
            "temperature",
            "unsupported_parameter",
            ProviderUnavailableError,
        ),
        (
            401,
            "invalid_api_key",
            None,
            "authentication_failed",
            ProviderUnavailableError,
        ),
        (403, None, None, "access_denied", ProviderUnavailableError),
        (404, "model_not_found", "model", "model_not_found", ProviderUnavailableError),
        (429, "insufficient_quota", None, "quota_exceeded", ProviderTransientError),
        (429, "rate_limit_exceeded", None, "rate_limited", ProviderTransientError),
        (503, "server_is_overloaded", None, "server_error", ProviderTransientError),
    ],
)
def test_rejections_log_safe_categories_without_changing_exception_types(
    caplog: pytest.LogCaptureFixture,
    status: int,
    code: str | None,
    parameter: str | None,
    category: str,
    exception: type[Exception],
) -> None:
    caplog.set_level(logging.ERROR)
    response = _error_response(
        status,
        {"code": code, "param": parameter, "message": "SYNTHETIC_PRIVATE_MESSAGE"},
    )

    with pytest.raises(exception):
        classify_openai_response(
            response, model_tag="gpt-5-mini", operation="completion"
        )

    assert f"http_status={status}" in caplog.text
    assert f"error_category={category}" in caplog.text
    assert "SYNTHETIC_PRIVATE_MESSAGE" not in caplog.text


@pytest.mark.parametrize(
    "error",
    [
        None,
        [],
        "PRIVATE_FRAGMENT",
        {
            "code": {"secret": "PRIVATE_FRAGMENT"},
            "param": ["PRIVATE_FRAGMENT"],
            "message": "PRIVATE_FRAGMENT",
        },
        {
            "code": "sk-synthetic-secret",
            "param": "PRIVATE_FRAGMENT",
            "message": "PRIVATE_FRAGMENT",
        },
    ],
)
def test_untrusted_error_fields_never_become_log_fields(
    caplog: pytest.LogCaptureFixture, error: object
) -> None:
    caplog.set_level(logging.ERROR)

    with pytest.raises(ProviderUnavailableError):
        classify_openai_response(
            _error_response(400, error), model_tag="gpt-5-mini", operation="embedding"
        )

    assert "provider_error_code=unknown" in caplog.text
    assert "parameter=unknown" in caplog.text
    assert "PRIVATE_FRAGMENT" not in caplog.text
    assert "sk-synthetic-secret" not in caplog.text


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"\xff",
        b"[]",
        b"[" * 10000 + b"0" + b"]" * 10000,
        b'{"error":{"code":"invalid_json_schema"}}' + b" " * 65536,
    ],
)
def test_malformed_or_oversized_bodies_cannot_mask_http_failure(
    caplog: pytest.LogCaptureFixture, body: bytes
) -> None:
    caplog.set_level(logging.ERROR)

    with pytest.raises(ProviderUnavailableError):
        classify_openai_response(
            HttpResponse(400, body, {}), model_tag="gpt-5-mini", operation="completion"
        )

    assert "provider_error_code=unknown" in caplog.text
    assert "http_status=400" in caplog.text


def test_retry_after_remains_available_on_transient_errors() -> None:
    response = HttpResponse(429, b"{}", {"retry-after": "2"})

    with pytest.raises(ProviderTransientError) as captured:
        classify_openai_response(
            response, model_tag="gpt-5-mini", operation="completion"
        )

    assert captured.value.rate_limited
    assert captured.value.retry_after_seconds == 2


def test_success_is_not_logged_as_a_failure(caplog: pytest.LogCaptureFixture) -> None:
    classify_openai_response(
        HttpResponse(200, b"{}", {}), model_tag="gpt-5-mini", operation="completion"
    )

    assert "provider.request_failed" not in caplog.text


@pytest.mark.parametrize("operation", ["completion", "embedding", "tool_calling"])
def test_each_openai_adapter_logs_its_operation(
    caplog: pytest.LogCaptureFixture, operation: str
) -> None:
    caplog.set_level(logging.ERROR)
    transport = SequenceTransport(
        [
            _error_response(
                400,
                {"param": "response_format", "message": "SYNTHETIC_PRIVATE_MESSAGE"},
            )
        ]
    )
    options: _AdapterOptions = {
        "api_key": "synthetic-key",
        "model_tag": "synthetic-model",
        "transport": transport,
        "resilience": ResiliencePolicy(timeout_seconds=1, max_retries=0),
    }

    with pytest.raises(ProviderUnavailableError):
        if operation == "completion":
            OpenAICompletionAdapter(**options).complete(
                CompletionRequest(
                    system="synthetic", user="synthetic", max_output_tokens=8
                )
            )
        elif operation == "embedding":
            OpenAIEmbeddingAdapter(**options).embed(
                EmbeddingRequest(texts=("synthetic",), max_chars_per_text=100)
            )
        else:
            OpenAIToolCaller(**options).complete(
                ToolCallingRequest(
                    system="synthetic",
                    messages=(ChatMessage(role="user", content="synthetic"),),
                    tools=(),
                    max_output_tokens=8,
                )
            )

    assert f"operation={operation}" in caplog.text
    assert "provider_id=openai" in caplog.text
    assert "model_tag=synthetic-model" in caplog.text
    assert len(transport.calls) == 1
    assert "SYNTHETIC_PRIVATE_MESSAGE" not in caplog.text
