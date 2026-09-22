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


def test_course_does_not_meet_production_leadership() -> None:
    """PLAN 13D.5 — the API must not score an introductory course as leadership."""
    client = TestClient(create_app())
    uploaded = client.post(
        "/api/cv",
        json={
            "text": "Experience\n- Completed an introductory Python course.\n",
            "filename": "cv.txt",
        },
    )
    assert uploaded.status_code == 201
    created = client.post(
        "/api/roles",
        json={
            "title": "Platform Engineer",
            "company": "Northwind",
            "description": (
                "Requirements\n"
                "- Five years leading production Python systems\n"
            ),
        },
    )
    assert created.status_code == 202
    role = created.json()["role"]
    assert role["status"] == "ready"
    assert role["fitScore"] == 0
    requirements = client.get(f"/api/roles/{role['id']}/requirements")
    assert requirements.status_code == 200
    rows = requirements.json()
    assert rows
    assert all(row["status"] == "missing" for row in rows)
    assert all(row["evidence"] is None for row in rows)


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


def test_ready_role_includes_prose_fit_summary() -> None:
    client, role_id = _ready_client()
    listed = client.get("/api/roles").json()
    assert listed
    assert listed[0].get("fitSummary") is None
    role = client.get(f"/api/roles/{role_id}")
    assert role.status_code == 200
    summary = role.json()["fitSummary"]
    assert isinstance(summary, str) and summary
    lowered = summary.lower()
    assert "strongest match" in lowered
    assert "biggest gap" in lowered
    requirements = client.get(f"/api/roles/{role_id}/requirements").json()
    texts = [row["text"] for row in requirements]
    assert any(text in summary for text in texts)


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
    blob = str(body).lower()
    assert "owned dbt models in production" in blob

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


def test_ranking_assigns_shared_rank_to_equal_scores() -> None:
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
    by_id = {row["role"]["id"]: row for row in ranking.json()}
    assert by_id[role_a]["role"]["fitScore"] == by_id[role_b]["role"]["fitScore"]
    assert by_id[role_a]["rank"] == by_id[role_b]["rank"]
    assert by_id[role_a]["tied"] is True
    assert by_id[role_b]["tied"] is True


def test_compare_differentiator_names_a_status_distinction() -> None:
    client, role_a = _ready_client()
    second = client.post(
        "/api/roles",
        json={
            "title": "Platform Engineer",
            "company": "Kestrel",
            "description": """Requirements
- Must have production dbt experience
- Must have CUDA experience
Nice to have
- Looker dashboards
""",
        },
    )
    assert second.status_code == 202
    role_b = second.json()["role"]["id"]

    compare = client.get(f"/api/compare?a={role_a}&b={role_b}")
    assert compare.status_code == 200
    body = compare.json()
    differentiator = body["differentiator"].lower()
    assert "looker" not in differentiator
    assert "sql" in differentiator or "cuda" in differentiator
