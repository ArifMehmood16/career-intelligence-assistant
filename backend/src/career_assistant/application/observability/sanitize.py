"""Redact audit fields before they reach any store — never document text."""

from __future__ import annotations

from collections.abc import Mapping

from career_assistant.application.observability.names import (
    ACTIONS,
    ATTRIBUTE_KEY_PREFIXES,
    ENTITY_TYPES,
    EVENT_LEVELS,
    EVENTS,
    HTTP_METHODS,
    OUTCOMES,
    QUERY_ID_KEYS,
    UNKNOWN_ACTION,
    UNKNOWN_EVENT,
)
from career_assistant.application.ports.observability import (
    ActionRecord,
    EventRecord,
    HttpEnvelope,
)
from career_assistant.logconfig import redact_text

_MAX_NAME = 64
_MAX_PATH = 256
_MAX_LOGGER = 128
_MAX_VALUE = 200
_SAFE_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789._")


def _clip_name(value: str, *, fallback: str) -> str:
    lowered = value.strip().lower()
    cleaned = "".join(char if char in _SAFE_NAME_CHARS else "." for char in lowered)[
        :_MAX_NAME
    ]
    return cleaned or fallback


def _safe_name(value: str, allowed: frozenset[str], *, unknown: str) -> str:
    if value in allowed:
        return value
    return unknown


def _safe_optional_name(value: str | None, allowed: frozenset[str]) -> str | None:
    if value is None or value == "":
        return None
    if value in allowed:
        return value
    return None


def _safe_text(value: str | None, *, limit: int) -> str:
    if not value:
        return ""
    text = redact_text(value)
    if "\n" in text or "\r" in text:
        return "<redacted multiline>"
    if len(text) > limit:
        return f"<redacted len={len(text)}>"
    return text


def sanitize_attributes(
    attributes: Mapping[str, str | int | bool],
) -> dict[str, str | int | bool]:
    cleaned: dict[str, str | int | bool] = {}
    for key, value in attributes.items():
        if not any(key.startswith(prefix) for prefix in ATTRIBUTE_KEY_PREFIXES):
            continue
        if isinstance(value, bool) or isinstance(value, int):
            cleaned[key] = value
            continue
        if not isinstance(value, str):
            continue
        text = _safe_text(value, limit=_MAX_VALUE)
        if text.startswith("<redacted"):
            continue
        cleaned[key] = text
    return cleaned


def sanitize_action(record: ActionRecord) -> ActionRecord:
    outcome = record.outcome if record.outcome in OUTCOMES else "failed"
    return ActionRecord(
        id=_safe_text(record.id, limit=_MAX_NAME) or record.id,
        workspace_id=_safe_text(record.workspace_id, limit=_MAX_NAME)
        or record.workspace_id,
        correlation_id=_safe_text(record.correlation_id, limit=_MAX_LOGGER),
        action=_safe_name(record.action, ACTIONS, unknown=UNKNOWN_ACTION),
        outcome=outcome,
        duration_ms=max(0, record.duration_ms),
        entity_type=_safe_optional_name(record.entity_type, ENTITY_TYPES),
        entity_id=_safe_text(record.entity_id, limit=_MAX_NAME) or None,
        error_code=_clip_name(record.error_code or "", fallback="") or None,
        actor="workspace",
        attributes=sanitize_attributes(record.attributes),
    )


def sanitize_event(record: EventRecord) -> EventRecord:
    event = record.event
    if event not in EVENTS and not event.startswith("sql."):
        event = UNKNOWN_EVENT
    elif event.startswith("sql."):
        event = _clip_name(event, fallback=UNKNOWN_EVENT)
    level = record.level if record.level in EVENT_LEVELS else "info"
    return EventRecord(
        id=_safe_text(record.id, limit=_MAX_NAME) or record.id,
        correlation_id=_safe_text(record.correlation_id, limit=_MAX_LOGGER),
        logger_name=_safe_text(record.logger_name, limit=_MAX_LOGGER),
        event=event,
        workspace_id=_safe_text(record.workspace_id, limit=_MAX_NAME) or None,
        action_id=_safe_text(record.action_id, limit=_MAX_NAME) or None,
        level=level,
        job_id=_safe_text(record.job_id, limit=_MAX_NAME) or None,
        role_id=_safe_text(record.role_id, limit=_MAX_NAME) or None,
        document_id=_safe_text(record.document_id, limit=_MAX_NAME) or None,
        attributes=sanitize_attributes(record.attributes),
    )


def sanitize_http(envelope: HttpEnvelope) -> HttpEnvelope:
    method = envelope.method.upper()
    if method not in HTTP_METHODS:
        method = "GET"
    path = envelope.path.split("?", 1)[0]
    path = _safe_text(path, limit=_MAX_PATH) or "/"
    query: dict[str, str] = {}
    for key, value in envelope.query_id_keys.items():
        if key not in QUERY_ID_KEYS:
            continue
        text = _safe_text(value, limit=_MAX_NAME)
        if text and not text.startswith("<redacted"):
            query[key] = text
    return HttpEnvelope(
        id=_safe_text(envelope.id, limit=_MAX_NAME) or envelope.id,
        correlation_id=_safe_text(envelope.correlation_id, limit=_MAX_LOGGER),
        method=method,
        path=path,
        status=envelope.status,
        duration_ms=max(0, envelope.duration_ms),
        workspace_id=_safe_text(envelope.workspace_id, limit=_MAX_NAME) or None,
        request_bytes=envelope.request_bytes,
        response_bytes=envelope.response_bytes,
        error_code=_clip_name(envelope.error_code or "", fallback="") or None,
        query_id_keys=query,
    )
