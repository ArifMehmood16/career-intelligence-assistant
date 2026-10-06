"""PLAN 18.10 — the v2 verdict and trace routes: wire shape and status codes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from career_assistant.application.ports.search import RetrievalTrace
from career_assistant.application.ports.v2_results import (
    StoredEvidence,
    StoredVerdict,
    V2RoleResult,
)
from career_assistant.domain.judging import (
    Adjustment,
    JudgedVerdict,
    ProposedQuote,
    ProposedScore,
)
from career_assistant.domain.scoring_v2 import Dimension, Gap, KeywordCoverage
from career_assistant.domain.search import SearchHit
from career_assistant.main import create_app

REQUIREMENT = "0b6d8f9e-3f51-5d6b-9a39-6f7e1c2d4a10"

_CV = """Experience
Senior Analytics Engineer — Acme — 2022-01 — Present
- Owned dbt models in production for the warehouse.
"""

_JD = """Requirements
- Must have production dbt experience
"""

_VERDICT = JudgedVerdict(
    requirement_id=REQUIREMENT,
    verdict="partial",
    match_score=2,
    match_rationale="Owned dbt models; production scale is not stated.",
    evidence=(ProposedQuote("chunk-1", "Owned dbt models in production"),),
    seniority=ProposedScore(3, "Senior title."),
    experience=None,
    unmet_conditions=("production scale",),
    contradiction=False,
    sufficient=True,
    rewrite_query=None,
    adjustments=(Adjustment.VERDICT_LOWERED,),
)

_RESULT = V2RoleResult(
    analysis_id="job-1",
    score=61.5,
    band="partial",
    gated=False,
    rubric_version="scoring-rubric-v2",
    left_machine=False,
    verdicts=(
        StoredVerdict(
            requirement_id=REQUIREMENT,
            quote="Must have production dbt experience",
            statement="Production dbt experience",
            must_have=True,
            verdict=_VERDICT,
            requirement_score=0.61,
            evidence=(
                StoredEvidence("chunk-1", "doc-cv", "Owned dbt models in production"),
            ),
            provider_id="hermetic",
            model_tag="rules-v1",
        ),
    ),
    coverage=KeywordCoverage(exact=("dbt",), alias=(), missing=("airflow",)),
    gaps=(Gap(REQUIREMENT, Dimension.MATCH, 0.61, 12.5),),
)

_TRACES = (
    RetrievalTrace("v-1", 1, "dbt at production scale", ()),
    RetrievalTrace(
        "v-1", 0, "production dbt", (SearchHit("chunk-1", 0.03, 1, 2, None),)
    ),
)


class _Reader:
    def result(self, workspace_id: str, role_id: str) -> V2RoleResult | None:
        return _RESULT

    def traces(
        self, workspace_id: str, role_id: str, requirement_id: str
    ) -> tuple[RetrievalTrace, ...] | None:
        return _TRACES if requirement_id == REQUIREMENT else None


def _client_with_role(*, published: bool) -> tuple[TestClient, str]:
    client = TestClient(create_app(v2_results=_Reader() if published else None))
    assert (
        client.post("/api/cv", json={"text": _CV, "filename": "cv.txt"}).status_code
        == 201
    )
    created = client.post(
        "/api/roles", json={"title": "AE", "company": "Acme", "description": _JD}
    )
    assert created.status_code == 202
    return client, created.json()["role"]["id"]


def test_verdicts_are_returned_in_the_contract_shape() -> None:
    client, role_id = _client_with_role(published=True)

    body = client.get(f"/api/roles/{role_id}/verdicts").json()

    assert body["roleId"] == role_id
    assert body["fitScore"] == 61.5
    assert body["keywordCoverage"] == {
        "exact": ["dbt"],
        "alias": [],
        "missing": ["airflow"],
    }
    assert body["gapPlan"] == [
        {
            "requirementId": REQUIREMENT,
            "dimension": "match",
            "current": 0.61,
            "delta": 12.5,
        }
    ]
    verdict = body["verdicts"][0]
    assert verdict["scoreImpact"] is None
    assert verdict["match"] == {
        "score": 2,
        "rationale": "Owned dbt models; production scale is not stated.",
    }
    assert verdict["seniority"] == {"score": 3, "rationale": "Senior title."}
    assert verdict["experience"] is None
    assert verdict["adjustments"] == ["verdict_lowered_to_partial"]
    assert verdict["unmetConditions"] == ["production scale"]
    assert verdict["evidence"] == [
        {
            "chunkId": "chunk-1",
            "documentId": "doc-cv",
            "quote": "Owned dbt models in production",
        }
    ]
    assert (verdict["provider"], verdict["model"]) == ("hermetic", "rules-v1")


def test_trace_rounds_are_in_order() -> None:
    client, role_id = _client_with_role(published=True)

    body = client.get(f"/api/roles/{role_id}/verdicts/{REQUIREMENT}/trace").json()

    assert [r["round"] for r in body["rounds"]] == [0, 1]
    assert body["rounds"][0]["hits"] == [
        {
            "chunkId": "chunk-1",
            "fusedScore": 0.03,
            "denseRank": 1,
            "lexicalRank": 2,
            "exactRank": None,
        }
    ]


def test_an_unknown_requirement_is_not_found() -> None:
    client, role_id = _client_with_role(published=True)

    response = client.get(f"/api/roles/{role_id}/verdicts/other/trace")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "requirement_not_found"


def test_the_default_fixture_store_exposes_current_verdicts() -> None:
    client, role_id = _client_with_role(published=False)

    verdicts = client.get(f"/api/roles/{role_id}/verdicts")
    trace = client.get(f"/api/roles/{role_id}/verdicts/{REQUIREMENT}/trace")

    assert verdicts.status_code == 200
    assert verdicts.json()["verdicts"]
    # This id belongs to the injected-reader fixture, not the actual publication.
    assert trace.status_code == 404


def test_an_unknown_role_is_not_found_on_both_routes() -> None:
    client = TestClient(create_app(v2_results=_Reader()))

    for path in ("verdicts", f"verdicts/{REQUIREMENT}/trace"):
        response = client.get(f"/api/roles/missing/{path}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "role_not_found"
