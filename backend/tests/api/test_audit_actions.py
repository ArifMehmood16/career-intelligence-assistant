"""Phase 15B.5 — use-case actions on the audit recorder, never document text."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.application.observability.memory import InMemoryAuditRecorder
from career_assistant.logconfig import configure_logging
from career_assistant.main import create_app

_PLANTED = "PLANTED_CV_PHRASE_MUST_NOT_APPEAR_IN_LOGS_9f3c2a"


def _recorder(client: TestClient) -> InMemoryAuditRecorder:
    recorder = client.app.state.audit_recorder
    assert isinstance(recorder, InMemoryAuditRecorder)
    return recorder


def test_cv_upload_records_succeeded_action_without_document_text() -> None:
    configure_logging(force=True)
    client = TestClient(create_app())

    response = client.post(
        "/api/cv",
        files={
            "file": (
                "cv.txt",
                f"Owned dbt models. {_PLANTED}\n".encode(),
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    actions = [row for row in _recorder(client).actions if row.action == "cv.upload"]
    assert actions
    row = actions[-1]
    assert row.outcome == "succeeded"
    assert row.entity_id == response.json()["id"]
    assert "count_spans" in row.attributes
    assert _PLANTED not in repr(row)


def test_unsupported_cv_records_failed_action_with_error_code() -> None:
    configure_logging(force=True)
    client = TestClient(create_app())

    response = client.post(
        "/api/cv",
        files={"file": ("x.bin", b"\x00\x01\x02\x03", "application/octet-stream")},
    )

    assert response.status_code == 415
    actions = [row for row in _recorder(client).actions if row.action == "cv.upload"]
    assert actions
    row = actions[-1]
    assert row.outcome == "failed"
    assert row.error_code == "document_unsupported"


def test_role_create_and_cv_delete_record_actions() -> None:
    configure_logging(force=True)
    client = TestClient(create_app())
    client.post(
        "/api/cv",
        files={"file": ("cv.txt", b"Owned dbt models in production.\n", "text/plain")},
    )

    created = client.post(
        "/api/roles",
        json={
            "title": "Analytics Engineer",
            "company": "Acme",
            "description": f"Must have dbt. {_PLANTED}\n",
        },
    )
    assert created.status_code == 202
    role_id = created.json()["role"]["id"]
    roles = [row for row in _recorder(client).actions if row.action == "role.create"]
    assert roles
    assert roles[-1].outcome == "accepted"
    assert roles[-1].entity_id == role_id
    assert _PLANTED not in repr(roles[-1])

    deleted = client.delete("/api/cv")
    assert deleted.status_code == 204
    deletes = [row for row in _recorder(client).actions if row.action == "cv.delete"]
    assert deletes
    assert deletes[-1].outcome == "succeeded"


def test_provider_change_records_ids_only() -> None:
    configure_logging(force=True)
    client = TestClient(create_app())

    response = client.put(
        "/api/settings/providers",
        json={
            "answerProviderId": "hermetic",
            "answerModel": "rules-v1",
            "indexProviderId": "hermetic",
            "indexModel": "lexical-hash-v1",
            "acknowledgedEgress": False,
        },
    )

    assert response.status_code == 200
    actions = [
        row
        for row in _recorder(client).actions
        if row.action == "settings.provider_changed"
    ]
    assert actions
    row = actions[-1]
    assert row.attributes["provider_completion"] == "hermetic"
    assert row.attributes["provider_embedding"] == "hermetic"


def test_ask_records_action_without_question_text() -> None:
    configure_logging(force=True)
    client = TestClient(create_app())
    client.post(
        "/api/cv",
        json={
            "text": (
                "Experience\n"
                "Senior Analytics Engineer — Acme — 2022-01 — Present\n"
                "- Owned dbt models in production for the warehouse.\n"
            ),
            "filename": "cv.txt",
        },
    )
    role = client.post(
        "/api/roles",
        json={
            "title": "AE",
            "company": "Acme",
            "description": "Requirements\n- Must have production dbt experience\n",
        },
    )
    assert role.status_code == 202
    planted = f"What am I missing? {_PLANTED}"
    response = client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json={
            "content": planted,
            "roleId": role.json()["role"]["id"],
            "clientRequestId": "audit-ask-1",
        },
    )
    assert response.status_code == 200
    actions = [row for row in _recorder(client).actions if row.action == "ask.question"]
    assert actions
    dumped = repr(actions[-1])
    assert _PLANTED not in dumped
    assert planted not in dumped
