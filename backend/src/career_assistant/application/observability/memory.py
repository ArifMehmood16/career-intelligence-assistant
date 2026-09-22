"""Hermetic audit recorder — lists in process, no database."""

from __future__ import annotations

from career_assistant.application.observability.sanitize import (
    sanitize_action,
    sanitize_event,
    sanitize_http,
)
from career_assistant.application.ports.observability import (
    ActionRecord,
    EventRecord,
    HttpEnvelope,
)


class InMemoryAuditRecorder:
    def __init__(self) -> None:
        self._actions: list[ActionRecord] = []
        self._events: list[EventRecord] = []
        self._http: list[HttpEnvelope] = []

    def record_action(self, action: ActionRecord) -> None:
        self._actions.append(sanitize_action(action))

    def record_event(self, event: EventRecord) -> None:
        self._events.append(sanitize_event(event))

    def record_http(self, envelope: HttpEnvelope) -> None:
        self._http.append(sanitize_http(envelope))

    @property
    def actions(self) -> tuple[ActionRecord, ...]:
        return tuple(self._actions)

    @property
    def events(self) -> tuple[EventRecord, ...]:
        return tuple(self._events)

    @property
    def http(self) -> tuple[HttpEnvelope, ...]:
        return tuple(self._http)
