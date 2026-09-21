"""Phase 13A.6 — generated prose must go through grounded generation."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from pydantic import SecretStr
from tests.support.scripted_transport import ScriptedTransport

from career_assistant.adapters.providers.http_transport import HttpResponse
from career_assistant.main import create_app
from career_assistant.settings import ProviderSettings

_CV = """Experience
Senior Analytics Engineer — Acme — 2022-01 — Present
- Owned dbt models in production for the warehouse.
- Built SQL pipelines on Snowflake.
"""

_JD = """Requirements
- Must have production dbt experience
- Must have SQL warehousing skills
Nice to have
- Looker dashboards
"""

_JD_WITH_GAP = """Requirements
- Must have production dbt experience
- Must have SQL warehousing skills
- Must have CUDA experience
"""


def _ready_client(*, description: str = _JD) -> tuple[TestClient, str]:
    client = TestClient(create_app())
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    created = client.post(
        "/api/roles",
        json={
            "title": "Analytics Engineer",
            "company": "Acme",
            "description": description,
        },
    )
    assert created.status_code == 202
    return client, created.json()["role"]["id"]


def _letter_text(payload: dict[str, object]) -> str:
    paragraphs = payload["paragraphs"]
    assert isinstance(paragraphs, list)
    return "\n".join(str(item["text"]) for item in paragraphs if isinstance(item, dict))


def test_bullet_without_cited_claim_is_refused_not_persisted() -> None:
    client, role_id = _ready_client()
    requirements = client.get(f"/api/roles/{role_id}/requirements").json()
    missing = next(row for row in requirements if row["status"] == "missing")

    response = client.post(
        f"/api/roles/{role_id}/bullets",
        json={"requirementId": missing["id"]},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_cited_claims"
    export = client.get(f"/api/roles/{role_id}/export/bullets.md")
    assert export.status_code == 422
    assert export.json()["error"]["code"] == "validation_failed"


def test_cover_letter_honours_tone_and_honest_gap_line() -> None:
    client, role_id = _ready_client(description=_JD_WITH_GAP)

    plain = client.post(
        f"/api/roles/{role_id}/cover-letter",
        json={"tone": "plain", "includeGapLine": False},
    )
    warm = client.post(
        f"/api/roles/{role_id}/cover-letter",
        json={"tone": "warm", "includeGapLine": True},
    )
    assert plain.status_code == 200, plain.text
    assert warm.status_code == 200, warm.text
    plain_text = _letter_text(plain.json())
    warm_text = _letter_text(warm.json())
    assert "cuda" not in plain_text.lower()
    assert "cuda" in warm_text.lower()
    assert plain_text != warm_text


def test_cover_letter_uses_generation_pipeline_and_drops_invented_facts() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": "I led Kubernetes at Google for 12 years with CUDA."
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 8, "completion_tokens": 12},
    }
    transport = ScriptedTransport(
        {"/chat/completions": HttpResponse(200, json.dumps(payload).encode(), {})}
    )
    app = create_app(
        providers=ProviderSettings(
            completion_provider="hermetic",
            embedding_provider="hermetic",
            allow_hosted_providers=True,
            openai_api_key=SecretStr("sk-test-never-leave-the-fixture"),
            openai_completion_model="gpt-4o-mini",
            openai_embedding_model="text-embedding-3-small",
        )
    )
    app.state.http_transport = transport
    client = TestClient(app)
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    role_id = client.post(
        "/api/roles",
        json={
            "title": "Analytics Engineer",
            "company": "Acme",
            "description": _JD_WITH_GAP,
        },
    ).json()["role"]["id"]
    chosen = client.put(
        "/api/settings/providers",
        json={
            "answerProviderId": "openai",
            "answerModel": "gpt-4o-mini",
            "indexProviderId": "hermetic",
            "indexModel": "lexical-hash-v1",
            "acknowledgedEgress": True,
        },
    )
    assert chosen.status_code == 200
    calls_after_analysis = len(transport.calls)

    letter = client.post(
        f"/api/roles/{role_id}/cover-letter",
        json={"tone": "plain", "includeGapLine": False},
    )
    assert letter.status_code == 200, letter.text
    text = _letter_text(letter.json())
    assert "kubernetes" not in text.lower()
    assert "12 years" not in text.lower()
    assert letter.json()["provenance"]["fallback"] == "template"
    assert letter.json()["provenance"]["provider"] == "openai"
    assert len(transport.calls) > calls_after_analysis
