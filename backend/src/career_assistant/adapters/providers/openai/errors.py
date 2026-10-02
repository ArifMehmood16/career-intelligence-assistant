"""Content-free OpenAI request failure diagnostics, before shared retry policy."""

from __future__ import annotations

import json
import logging

from career_assistant.adapters.providers.http_transport import HttpResponse
from career_assistant.adapters.providers.resilience import classify_http_status
from career_assistant.logconfig import log_failure

_log = logging.getLogger(__name__)
_MAX_ERROR_BYTES = 65_536
_UNKNOWN = "unknown"
_QUOTA_CODES = frozenset(
    {
        "insufficient_quota",
        "credit_balance_exhausted",
        "organization_spend_limit_exceeded",
        "project_spend_limit_exceeded",
        "organization_usage_limit_exceeded",
    }
)
_CODE_CATEGORIES = {
    "invalid_json_schema": "invalid_schema",
    "unsupported_parameter": "unsupported_parameter",
    "unsupported_value": "unsupported_value",
    "invalid_api_key": "authentication_failed",
    "model_not_found": "model_not_found",
    "context_length_exceeded": "input_too_large",
    "rate_limit_exceeded": "rate_limited",
    "slow_down": "rate_limited",
    "server_is_overloaded": "server_error",
}
_KNOWN_CODES = frozenset(_CODE_CATEGORIES) | _QUOTA_CODES
_KNOWN_PARAMETERS = frozenset(
    {
        "model",
        "response_format",
        "response_format.json_schema",
        "temperature",
        "seed",
        "max_completion_tokens",
        "max_tokens",
        "messages",
        "input",
        "dimensions",
        "encoding_format",
        "tools",
    }
)
_STATUS_CATEGORIES = {
    400: "invalid_request",
    401: "authentication_failed",
    403: "access_denied",
    404: "not_found",
    429: "rate_limit_or_quota",
}


def classify_openai_response(
    response: HttpResponse, *, model_tag: str, operation: str
) -> None:
    """Log fixed categories, never vendor messages, then retain HTTP semantics."""
    if response.status_code < 400:
        return
    code, parameter = _safe_details(response.body)
    log_failure(
        _log,
        "provider.request_failed",
        provider_id="openai",
        model_tag=model_tag,
        operation=operation,
        http_status=response.status_code,
        error_category=_category(response.status_code, code, parameter),
        provider_error_code=code,
        parameter=parameter,
    )
    classify_http_status(response.status_code, response.headers)


def _safe_details(body: bytes) -> tuple[str, str]:
    if len(body) > _MAX_ERROR_BYTES:
        return _UNKNOWN, _UNKNOWN
    try:
        payload = json.loads(body)
    except ValueError, RecursionError:
        return _UNKNOWN, _UNKNOWN
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return _UNKNOWN, _UNKNOWN
    return (
        _allowlisted(error.get("code"), _KNOWN_CODES),
        _allowlisted(error.get("param"), _KNOWN_PARAMETERS),
    )


def _allowlisted(value: object, choices: frozenset[str]) -> str:
    return value if isinstance(value, str) and value in choices else _UNKNOWN


def _category(status: int, code: str, parameter: str) -> str:
    if status >= 500:
        return "server_error"
    if code in _QUOTA_CODES:
        return "quota_exceeded"
    if code in _CODE_CATEGORIES:
        return _CODE_CATEGORIES[code]
    if status == 400 and parameter in {
        "response_format",
        "response_format.json_schema",
    }:
        return "request_format_rejected"
    return _STATUS_CATEGORIES.get(status, "request_rejected")
