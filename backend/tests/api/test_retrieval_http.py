"""Phase 13A.5 — Ask retrieval includes supporting letters and same-role JDs."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.main import create_app

_CV = """Experience
Senior Analytics Engineer — Acme — 2022-01 — Present
- Owned dbt models in production for the warehouse.
"""

_LETTER = """Dear Hiring Manager,

I wrote about Kubernetes operators in my cover letter.

Kind regards
"""


def _cover_letter_span_id(client: TestClient, *, containing: str) -> str:
    workspace_id = client.cookies["workspace"]
    stored = next(
        iter(client.app.state.supporting_store._letters[workspace_id].values())
    )
    needle = containing.lower()
    for span in stored.spans:
        if needle in span.text.lower():
            return span.id
    raise AssertionError(f"cover letter has no span containing {containing!r}")


def test_open_question_cites_cover_letter_when_asked() -> None:
    client = TestClient(create_app())
    assert (
        client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"}).status_code
        == 201
    )
    created = client.post(
        "/api/cover-letters",
        json={"text": _LETTER, "filename": "letter.txt"},
    )
    assert created.status_code == 201
    span_id = _cover_letter_span_id(client, containing="Kubernetes")

    asked = client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json={
            "content": "What did I write in my cover letter about Kubernetes?",
            "clientRequestId": "cr-cover-letter-ask-1",
        },
    )
    assert asked.status_code == 200
    citation_ids = {item["id"] for item in asked.json()["citations"]}
    assert span_id in citation_ids

    evidence = client.get(f"/api/spans/{span_id}")
    assert evidence.status_code == 200
    assert "kubernetes" in evidence.json()["highlight"].lower()


def test_role_scoped_open_question_cannot_cite_other_role_jd() -> None:
    client = TestClient(create_app())
    assert (
        client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"}).status_code
        == 201
    )
    role_a = client.post(
        "/api/roles",
        json={
            "title": "GPU",
            "company": "Acme",
            "description": "Requirements\n- Need CUDA for GPU kernels.\n",
        },
    ).json()["role"]["id"]
    role_b = client.post(
        "/api/roles",
        json={
            "title": "Robotics",
            "company": "Acme",
            "description": "Requirements\n- Need ROS2 navigation stack.\n",
        },
    ).json()["role"]["id"]
    workspace_id = client.cookies["workspace"]
    analyses = client.app.state.role_store.analyses[workspace_id]
    assert analyses[role_a].jd_spans
    assert analyses[role_b].jd_spans
    span_a = analyses[role_a].jd_spans[0].id
    span_b = analyses[role_b].jd_spans[0].id

    asked = client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json={
            "content": "What does this role say about CUDA?",
            "roleId": role_a,
            "clientRequestId": "cr-role-scope-1",
        },
    )
    assert asked.status_code == 200
    citation_ids = {item["id"] for item in asked.json()["citations"]}
    assert span_a in citation_ids
    assert span_b not in citation_ids
