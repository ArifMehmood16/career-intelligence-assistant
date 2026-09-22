"""Phase 15B.3 — audit recorder stores ids and counts, never document text."""

from __future__ import annotations

from career_assistant.application.observability.memory import InMemoryAuditRecorder
from career_assistant.application.ports.observability import (
    ActionRecord,
    EventRecord,
    HttpEnvelope,
)

_PLANTED = "PLANTED_CV_PHRASE_MUST_NOT_APPEAR_IN_LOGS_9f3c2a"
_PLANTED_KEY = "sk-planted-secret-key-value-for-redaction"


def test_record_action_drops_planted_phrase_before_store() -> None:
    recorder = InMemoryAuditRecorder()

    recorder.record_action(
        ActionRecord(
            id="act-1",
            workspace_id="ws-1",
            correlation_id="corr-1",
            action="cv.upload",
            outcome="succeeded",
            duration_ms=12,
            entity_type="cv",
            entity_id="doc-1",
            attributes={
                "quote": _PLANTED,
                "id_document": "doc-1",
                "count_spans": 4,
                "secret": _PLANTED_KEY,
            },
        )
    )

    stored = recorder.actions[0]
    dumped = repr(stored.attributes)
    assert _PLANTED not in dumped
    assert _PLANTED_KEY not in dumped
    assert "quote" not in stored.attributes
    assert "secret" not in stored.attributes
    assert stored.attributes["id_document"] == "doc-1"
    assert stored.attributes["count_spans"] == 4
    assert stored.action == "cv.upload"


def test_unknown_action_name_is_not_stored_verbatim() -> None:
    recorder = InMemoryAuditRecorder()

    recorder.record_action(
        ActionRecord(
            id="act-2",
            workspace_id="ws-1",
            correlation_id="corr-2",
            action=f"invented.{_PLANTED}",
            outcome="succeeded",
            duration_ms=1,
        )
    )

    stored = recorder.actions[0]
    assert stored.action == "action.unknown"
    assert _PLANTED not in stored.action


def test_record_event_and_http_keep_safe_fields_only() -> None:
    recorder = InMemoryAuditRecorder()

    recorder.record_event(
        EventRecord(
            id="evt-1",
            workspace_id="ws-1",
            correlation_id="corr-3",
            logger_name="career_assistant.application.documents.cv",
            event="cv.uploaded",
            attributes={"excerpt": _PLANTED, "count_pages": 2},
        )
    )
    recorder.record_http(
        HttpEnvelope(
            id="http-1",
            workspace_id="ws-1",
            correlation_id="corr-3",
            method="POST",
            path="/api/cv",
            status=201,
            duration_ms=40,
            request_bytes=1200,
            error_code=None,
            query_id_keys={"q": _PLANTED, "roleId": "role-1"},
        )
    )

    event = recorder.events[0]
    assert event.event == "cv.uploaded"
    assert _PLANTED not in repr(event.attributes)
    assert event.attributes["count_pages"] == 2

    envelope = recorder.http[0]
    assert envelope.method == "POST"
    assert envelope.path == "/api/cv"
    assert envelope.status == 201
    assert envelope.query_id_keys["roleId"] == "role-1"
    assert _PLANTED not in repr(envelope.query_id_keys)
    assert not hasattr(envelope, "body")
