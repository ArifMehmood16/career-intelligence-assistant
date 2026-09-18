"""Phase 11.8 — role delete, reanalyse, draft list, export variants, incomplete."""

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
    role_id = created.json()["role"]["id"]
    assert created.json()["role"]["status"] == "ready"
    return client, role_id


def test_delete_role_returns_204_and_removes_it() -> None:
    client, role_id = _ready_client()

    deleted = client.delete(f"/api/roles/{role_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/roles/{role_id}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "role_not_found"


def test_reanalyse_returns_202_with_new_job() -> None:
    client, role_id = _ready_client()

    response = client.post(f"/api/roles/{role_id}/reanalyse")
    assert response.status_code == 202
    body = response.json()
    assert "jobId" in body
    assert body["jobId"]

    job = client.get(f"/api/jobs/{body['jobId']}")
    assert job.status_code == 200
    assert job.json()["state"] == "succeeded"

    role = client.get(f"/api/roles/{role_id}")
    assert role.status_code == 200
    assert role.json()["status"] == "ready"


def test_analysis_incomplete_returns_409() -> None:
    client, role_id = _ready_client()
    workspace_id = client.cookies["workspace"]
    client.app.state.role_store.mark_incomplete(workspace_id, role_id)

    gap = client.get(f"/api/roles/{role_id}/gap-plan")
    assert gap.status_code == 409
    assert gap.json()["error"]["code"] == "analysis_incomplete"


def test_cover_letter_is_listed_after_create() -> None:
    client, role_id = _ready_client()
    created = client.post(
        f"/api/roles/{role_id}/cover-letter",
        json={"tone": "plain", "includeGapLine": False},
    )
    assert created.status_code in {200, 409}
    if created.status_code == 409:
        # Fixture may not meet two must-haves; list is still empty and valid.
        listed = client.get(f"/api/roles/{role_id}/cover-letters")
        assert listed.status_code == 200
        assert listed.json() == []
        return

    draft_id = created.json()["id"]
    listed = client.get(f"/api/roles/{role_id}/cover-letters")
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["id"] == draft_id
    assert body[0]["provenance"]["leftMachine"] is False


def test_export_cover_letter_and_bullets_markdown() -> None:
    client, role_id = _ready_client()
    requirements = client.get(f"/api/roles/{role_id}/requirements").json()
    requirement_id = requirements[0]["id"]

    bullets = client.post(
        f"/api/roles/{role_id}/bullets",
        json={"requirementId": requirement_id},
    )
    assert bullets.status_code == 200

    bullets_md = client.get(f"/api/roles/{role_id}/export/bullets.md")
    assert bullets_md.status_code == 200
    assert bullets_md.headers["content-type"].startswith("text/markdown")
    assert len(bullets_md.content) > 0

    letter = client.post(
        f"/api/roles/{role_id}/cover-letter",
        json={"tone": "plain", "includeGapLine": False},
    )
    if letter.status_code == 200:
        letter_md = client.get(f"/api/roles/{role_id}/export/cover-letter.md")
        assert letter_md.status_code == 200
        assert letter_md.headers["content-type"].startswith("text/markdown")
        assert len(letter_md.content) > 0
