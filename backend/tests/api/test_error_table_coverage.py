"""Phase 11 exit gate — contract error codes reachable via the API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.application.documents.cv import reraise_intake_as_message
from career_assistant.application.intake.errors import IntakeError, IntakeErrorCode
from career_assistant.main import create_app
from career_assistant.settings import ProviderSettings


def test_intake_errors_map_to_contract_http_statuses() -> None:
    cases = {
        IntakeErrorCode.DOCUMENT_TOO_LARGE: 413,
        IntakeErrorCode.DOCUMENT_UNSUPPORTED: 415,
        IntakeErrorCode.DOCUMENT_UNREADABLE: 422,
    }
    for code, status in cases.items():
        mapped_code, _message, http_status = reraise_intake_as_message(
            IntakeError(code, "safe message")
        )
        assert mapped_code == code.value
        assert http_status == status


def test_provider_unavailable_when_index_is_anthropic() -> None:
    settings = ProviderSettings(
        allow_hosted_providers=True,
        anthropic_api_key="sk-test-key",
    )
    client = TestClient(create_app(providers=settings))
    response = client.put(
        "/api/settings/providers",
        json={
            "answerProviderId": "anthropic",
            "answerModel": "claude-sonnet-4-0",
            "indexProviderId": "anthropic",
            "indexModel": "n/a",
            "acknowledgedEgress": True,
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "provider_unavailable"
