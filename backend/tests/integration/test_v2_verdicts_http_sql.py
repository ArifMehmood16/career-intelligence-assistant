"""PLAN 18.10 — a v2 analysis is read back over HTTP: verdicts, traces, counts."""

from __future__ import annotations

import uuid
from collections import Counter

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.support.v2_http import SqlApp, analyse, queue_role, sql_app

pytestmark = pytest.mark.integration

_LABELS = {"met", "partial", "missing"}


def _v2_role(session_factory: sessionmaker[Session]) -> tuple[SqlApp, str]:
    app = sql_app(session_factory)
    role_id, _ = analyse(app)
    return app, role_id


def test_verdicts_show_the_fit_each_verdict_and_its_evidence(
    session_factory: sessionmaker[Session],
) -> None:
    app, role_id = _v2_role(session_factory)

    response = app.client.get(f"/api/roles/{role_id}/verdicts")

    assert response.status_code == 200, response.text
    body = response.json()
    role = app.client.get(f"/api/roles/{role_id}").json()
    assert round(body["fitScore"]) == role["fitScore"]
    assert body["leftMachine"] is False
    assert set(body["keywordCoverage"]) == {"exact", "alias", "missing"}
    assert isinstance(body["gapPlan"], list)
    assert body["verdicts"]
    impacts = [v["scoreImpact"] for v in body["verdicts"]]
    assert all(impact is not None for impact in impacts)
    assert sum(i["earned"] for i in impacts) == pytest.approx(body["fitScore"])
    assert sum(i["possible"] for i in impacts) == pytest.approx(100)
    for impact in impacts:
        assert impact["earned"] + impact["shortfall"] == pytest.approx(
            impact["possible"]
        )
    assert any(v["experienceExpected"] for v in body["verdicts"])
    for verdict in body["verdicts"]:
        if verdict["experienceExpected"]:
            assert verdict["experience"] is not None
            assert verdict["experienceExpected"] in verdict["quote"]
        assert verdict["verdict"] in _LABELS
        assert 0 <= verdict["match"]["score"] <= 3
        assert verdict["provider"] == "hermetic"
        for evidence in verdict["evidence"]:
            assert set(evidence) == {"chunkId", "documentId", "quote"}
            assert evidence["quote"]


def test_a_v2_role_counts_its_verdicts(
    session_factory: sessionmaker[Session],
) -> None:
    app, role_id = _v2_role(session_factory)

    verdicts = app.client.get(f"/api/roles/{role_id}/verdicts").json()["verdicts"]
    counts = app.client.get(f"/api/roles/{role_id}").json()["counts"]

    labels = Counter(verdict["verdict"] for verdict in verdicts)
    assert counts == {label: labels.get(label, 0) for label in _LABELS}


def test_a_trace_shows_what_the_judge_was_shown(
    session_factory: sessionmaker[Session],
) -> None:
    app, role_id = _v2_role(session_factory)
    verdicts = app.client.get(f"/api/roles/{role_id}/verdicts").json()["verdicts"]
    requirement_id = verdicts[0]["requirementId"]

    response = app.client.get(f"/api/roles/{role_id}/verdicts/{requirement_id}/trace")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["requirementId"] == requirement_id
    assert body["rounds"][0]["round"] == 0
    for hit in body["rounds"][0]["hits"]:
        assert hit["chunkId"]
        assert isinstance(hit["fusedScore"], float)


@pytest.mark.parametrize("requirement_id", [str(uuid.uuid4()), "not-a-uuid"])
def test_an_unknown_requirement_has_no_trace(
    session_factory: sessionmaker[Session], requirement_id: str
) -> None:
    app, role_id = _v2_role(session_factory)

    response = app.client.get(f"/api/roles/{role_id}/verdicts/{requirement_id}/trace")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "requirement_not_found"


def test_a_queued_role_has_no_verdicts(session_factory: sessionmaker[Session]) -> None:
    app = sql_app(session_factory)
    role_id, _ = queue_role(app)

    response = app.client.get(f"/api/roles/{role_id}/verdicts")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "analysis_incomplete"


def test_an_unknown_role_has_no_verdicts(
    session_factory: sessionmaker[Session],
) -> None:
    app = sql_app(session_factory)

    response = app.client.get(f"/api/roles/{uuid.uuid4()}/verdicts")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "role_not_found"


@pytest.mark.parametrize("route", ["requirements", "breakdown", "gap-plan"])
def test_analysis_views_read_the_current_publication(
    session_factory: sessionmaker[Session], route: str
) -> None:
    app, role_id = _v2_role(session_factory)

    response = app.client.get(f"/api/roles/{role_id}/{route}")

    assert response.status_code == 200, response.text


def test_a_role_says_which_pipeline_its_analysis_ran_on(
    session_factory: sessionmaker[Session],
) -> None:
    app, v2_role = _v2_role(session_factory)
    created = app.client.post(
        "/api/roles",
        json={"title": "Waiting", "company": "Acme", "description": "Python"},
    ).json()

    waiting = app.client.get(f"/api/roles/{created['role']['id']}").json()
    assert waiting["analysisPipeline"] is None

    app.worker.drain()

    listed = {r["id"]: r for r in app.client.get("/api/roles").json()}
    assert listed[v2_role]["analysisPipeline"] == "v2"
    assert listed[created["role"]["id"]]["analysisPipeline"] == "v2"
