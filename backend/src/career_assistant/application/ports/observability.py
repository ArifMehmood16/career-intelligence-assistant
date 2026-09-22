"""Observability records — ids, counts and codes only, never payloads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ActionRecord:
    id: str
    workspace_id: str
    correlation_id: str
    action: str
    outcome: str
    duration_ms: int
    entity_type: str | None = None
    entity_id: str | None = None
    error_code: str | None = None
    actor: str = "workspace"
    attributes: Mapping[str, str | int | bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EventRecord:
    id: str
    correlation_id: str
    logger_name: str
    event: str
    workspace_id: str | None = None
    action_id: str | None = None
    level: str = "info"
    job_id: str | None = None
    role_id: str | None = None
    document_id: str | None = None
    attributes: Mapping[str, str | int | bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HttpEnvelope:
    id: str
    correlation_id: str
    method: str
    path: str
    status: int
    duration_ms: int
    workspace_id: str | None = None
    request_bytes: int | None = None
    response_bytes: int | None = None
    error_code: str | None = None
    query_id_keys: Mapping[str, str] = field(default_factory=dict)


class AuditRecorder(Protocol):
    def record_action(self, action: ActionRecord) -> None: ...

    def record_event(self, event: EventRecord) -> None: ...

    def record_http(self, envelope: HttpEnvelope) -> None: ...
