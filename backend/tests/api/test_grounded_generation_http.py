"""Phase 13A.6 — generated prose must go through grounded generation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.main import create_app

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


def _ready_client() -> tuple[TestClient, str]:
    client = TestClient(create_app())
    client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"})
    created = client.post(
        "/api/roles",
        json={
            "title": "Analytics Engineer",
            "company": "Acme",
            "description": _JD,
        },
    )
    assert created.status_code == 202
    return client, created.json()["role"]["id"]


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
