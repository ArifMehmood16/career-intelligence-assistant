"""Phase 11.8 — role analysis output routes (requirements, gap, interview, drafts)."""

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
    # Hermetic path completes analysis synchronously for API contract tests.
    assert created.json()["role"]["status"] == "ready"
    return client, role_id


def test_requirements_and_gap_plan_for_ready_role() -> None:
    client, role_id = _ready_client()

    requirements = client.get(f"/api/roles/{role_id}/requirements")
    assert requirements.status_code == 200
    body = requirements.json()
    assert isinstance(body, list)
    assert body
    assert {"id", "roleId", "text", "type", "status", "evidence"} <= body[0].keys()

    breakdown = client.get(f"/api/roles/{role_id}/breakdown")
    assert breakdown.status_code == 200
    assert {row["id"] for row in breakdown.json()} >= {"must", "desirable"}

    gap = client.get(f"/api/roles/{role_id}/gap-plan")
    assert gap.status_code == 200
    plan = gap.json()
    assert plan["roleId"] == role_id
    assert "currentScore" in plan
    assert isinstance(plan["items"], list)


def test_interview_pack_and_export() -> None:
    client, role_id = _ready_client()

    pack = client.get(f"/api/roles/{role_id}/interview-pack")
    assert pack.status_code == 200
    body = pack.json()
    assert body["roleId"] == role_id
    assert "probes" in body
    assert "provenance" in body
    assert body["provenance"]["provider"] == "hermetic"
    assert body["provenance"]["leftMachine"] is False

    export = client.get(f"/api/roles/{role_id}/export/gap-plan.md")
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/markdown")
    assert b"#" in export.content or b"Gap" in export.content or len(export.content) > 0


def test_bullets_and_cover_letter_routes() -> None:
    client, role_id = _ready_client()
    requirements = client.get(f"/api/roles/{role_id}/requirements").json()
    requirement_id = requirements[0]["id"]

    bullets = client.post(
        f"/api/roles/{role_id}/bullets",
        json={"requirementId": requirement_id},
    )
    assert bullets.status_code == 200
    draft = bullets.json()
    assert draft["requirementId"] == requirement_id
    assert draft["provenance"]["grounded"] is True
    assert "provider" in draft["provenance"]

    letter = client.post(
        f"/api/roles/{role_id}/cover-letter",
        json={"tone": "plain", "includeGapLine": False},
    )
    # May refuse when fewer than two met must-haves — both outcomes are contract-valid.
    assert letter.status_code in {200, 409}
    if letter.status_code == 409:
        assert letter.json()["error"]["code"] == "insufficient_matched_requirements"
    else:
        assert letter.json()["provenance"]["leftMachine"] is False


def test_ranking_and_compare() -> None:
    client, role_a = _ready_client()
    second = client.post(
        "/api/roles",
        json={
            "title": "Data Engineer",
            "company": "Beta",
            "description": _JD,
        },
    )
    assert second.status_code == 202
    role_b = second.json()["role"]["id"]

    ranking = client.get("/api/ranking")
    assert ranking.status_code == 200
    ranked = ranking.json()
    assert len(ranked) >= 2
    assert ranked[0]["rank"] == 1
    assert "because" in ranked[0]

    compare = client.get(f"/api/compare?a={role_a}&b={role_b}")
    assert compare.status_code == 200
    body = compare.json()
    assert body["a"]["id"] == role_a
    assert body["b"]["id"] == role_b
    assert "shared" in body
    assert "differentiator" in body
