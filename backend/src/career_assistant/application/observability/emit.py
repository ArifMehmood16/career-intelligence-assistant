"""Fail-open action recording bound to the current request."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from contextvars import ContextVar

from career_assistant.application.ports.observability import ActionRecord, AuditRecorder
from career_assistant.logconfig import correlation_id_var, log_event, workspace_id_var

_log = logging.getLogger(__name__)
_recorder: ContextVar[AuditRecorder | None] = ContextVar("audit_recorder", default=None)


def bind_recorder(recorder: AuditRecorder | None) -> None:
    _recorder.set(recorder)


def clear_recorder() -> None:
    _recorder.set(None)


def emit_action(
    action: str,
    *,
    outcome: str,
    duration_ms: int = 0,
    entity_type: str | None = None,
    entity_id: str | None = None,
    error_code: str | None = None,
    attributes: Mapping[str, str | int | bool] | None = None,
) -> None:
    recorder = _recorder.get()
    if recorder is None:
        return
    workspace_id = workspace_id_var.get()
    if workspace_id in {"", "-"}:
        workspace_id = "unknown"
    try:
        recorder.record_action(
            ActionRecord(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                correlation_id=correlation_id_var.get(),
                action=action,
                outcome=outcome,
                duration_ms=max(0, duration_ms),
                entity_type=entity_type,
                entity_id=entity_id,
                error_code=error_code,
                attributes=dict(attributes or {}),
            )
        )
    except Exception:
        log_event(_log, "http.error", code="audit_failed", path=action)
