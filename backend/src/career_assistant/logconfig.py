"""Operational logging — stderr, field-based, never document or secret payloads.

stdlib only. Domain stays silent. Application, adapters and HTTP log events with
ids, counts and durations. Failures include ``site=module.function`` so the
operator can see which file and method emitted the failure. ``input`` fields are
safe descriptors (ids, counts, stages) — never document text, prompts or bodies.
"""

from __future__ import annotations

import inspect
import logging
import os
import re
import sys
from contextvars import ContextVar
from typing import TextIO

_MAX_FIELD_CHARS = 200
_SECRET_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9_-]{8,})|(Bearer\s+[A-Za-z0-9._~+/=-]{8,})",
    re.IGNORECASE,
)

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")
workspace_id_var: ContextVar[str] = ContextVar("workspace_id", default="-")

_configured = False
_secret_values: tuple[str, ...] = ()


def format_fields(**fields: object) -> str:
    """Render key=value pairs; drop multiline and over-long values."""
    parts: list[str] = []
    for key, value in fields.items():
        if value is None:
            continue
        text = str(value)
        if "\n" in text or "\r" in text:
            parts.append(f"{key}=<redacted multiline>")
            continue
        if len(text) > _MAX_FIELD_CHARS:
            parts.append(f"{key}=<redacted len={len(text)}>")
            continue
        parts.append(f"{key}={text}")
    return " ".join(parts)


def redact_text(value: str) -> str:
    redacted = _SECRET_PATTERN.sub("[redacted]", value)
    for secret in _secret_values:
        if secret and secret in redacted:
            redacted = redacted.replace(secret, "[redacted]")
    return redacted


def bind_request_context(*, correlation_id: str, workspace_id: str | None) -> None:
    correlation_id_var.set(correlation_id)
    workspace_id_var.set(workspace_id or "-")


def clear_request_context() -> None:
    correlation_id_var.set("-")
    workspace_id_var.set("-")


def caller_site(*, depth: int = 2) -> str:
    """Return ``module.function`` for the caller at ``depth`` frames up."""
    frame = inspect.currentframe()
    try:
        for _ in range(depth):
            if frame is None:
                return "unknown"
            frame = frame.f_back
        if frame is None:
            return "unknown"
        module = frame.f_globals.get("__name__", "unknown")
        return f"{module}.{frame.f_code.co_name}"
    finally:
        del frame


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        record.workspace_id = workspace_id_var.get()
        return True


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: redact_text(val) if isinstance(val, str) else val
                    for key, val in record.args.items()
                }
            else:
                record.args = tuple(
                    redact_text(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True


def configure_logging(
    *,
    stream: TextIO | None = None,
    force: bool = False,
    secret_values: tuple[str, ...] = (),
) -> None:
    """Attach a stderr handler to career_assistant. Safe to call more than once."""
    global _configured, _secret_values
    if secret_values:
        _secret_values = tuple(value for value in secret_values if value)
    if _configured and not force:
        return

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setLevel(logging.INFO)
    handler.addFilter(ContextFilter())
    handler.addFilter(RedactingFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s "
            "correlation_id=%(correlation_id)s workspace_id=%(workspace_id)s"
        )
    )

    log = logging.getLogger("career_assistant")
    log.handlers.clear()
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    # Propagate so pytest caplog sees records; uvicorn will not double them
    # because this logger's handler is the application stream.
    log.propagate = True

    _configured = True


def log_event(logger: logging.Logger, event: str, **fields: object) -> None:
    extra = format_fields(**fields)
    if extra:
        logger.info("%s %s", event, extra)
    else:
        logger.info("%s", event)



def log_failure(logger: logging.Logger, event: str, **fields: object) -> None:
    """ERROR-level failure with ``site=module.function`` when not supplied.

    ``input`` must be a safe descriptor (ids, counts, stages). Never pass
    document text, prompts, bodies or secrets.
    """
    if "site" not in fields:
        fields["site"] = caller_site(depth=2)
    extra = format_fields(**fields)
    if extra:
        logger.error("%s %s", event, extra)
    else:
        logger.error("%s", event)


def load_secret_values() -> tuple[str, ...]:
    """Env-derived secrets for the redacting filter. Empty when unset."""
    values: list[str] = []
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        raw = os.environ.get(name, "").strip()
        if raw:
            values.append(raw)
    return tuple(values)
