"""Every SQL-backed result consumer uses one current validated publication."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker
from tests.support.v2_http import SqlApp, analyse, sql_app

from career_assistant.adapters.persistence.models import (
    Base,
    ScoreExplanationRow,
    WorkspaceRow,
)
from career_assistant.application.ask.registry import ToolRegistry
from career_assistant.application.ask.workspace_tools import workspace_registry
from career_assistant.application.ports.v2_results import V2RoleResult

pytestmark = pytest.mark.integration


@dataclass(frozen=True)
class Published:
    app: SqlApp
    role: str
    result: V2RoleResult

    @property
    def workspace(self) -> str:
        return self.app.client.cookies["workspace"]

    def tools(self) -> ToolRegistry:
        state = self.app.client.app.state
        return workspace_registry(
            self.workspace,
            roles=state.role_store,
            cv_store=state.cv_store,
            supporting_store=state.supporting_store,
        )

    def ask(self, question: str) -> dict:
        response = self.app.client.post(
            "/api/messages",
            headers={"Accept": "application/json"},
            json={
                "content": question,
                "roleId": self.role,
                "clientRequestId": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 200, response.text
        return response.json()


@pytest.fixture()
def published(session_factory: sessionmaker[Session]) -> Published:
    app = sql_app(session_factory)
    role, _ = analyse(app)
    with app.uow_factory() as uow:
        result = uow.v2.result(app.client.cookies["workspace"], role)
    assert result is not None
    return Published(app, role, result)


def _requirements(world: Published) -> list[dict]:
    response = world.app.client.get(f"/api/roles/{world.role}/requirements")
    assert response.status_code == 200
    return response.json()


def _assert_publication_consumers(world: Published) -> None:
    client, path, result = world.app.client, f"/api/roles/{world.role}", world.result
    accountant = client.app.state.call_accountant
    before_calls = accountant.records
    summary = client.get(path).json()
    verdicts = client.get(f"{path}/verdicts").json()
    gaps = client.get(f"{path}/gap-plan").json()
    ranking = client.get("/api/ranking").json()
    expected = {item.requirement_id: item.verdict.verdict for item in result.verdicts}
    assert summary["status"] == "ready"
    assert summary["fitScore"] == round(result.score)
    assert verdicts["fitScore"] == result.score
    assert gaps["currentScore"] == result.score
    assert ranking[0]["role"]["id"] == world.role
    assert ranking[0]["role"]["fitScore"] == round(result.score)
    assert {row["id"]: row["status"] for row in _requirements(world)} == expected
    assert {
        row["requirementId"]: row["verdict"] for row in verdicts["verdicts"]
    } == expected
    assert {row["requirementId"]: row["scoreDelta"] for row in gaps["items"]} == {
        gap.requirement_id: gap.delta
        for gap in result.gaps
        if expected[gap.requirement_id] != "met"
    }
    tools = world.tools()
    analysis = tools.call("get_role_analysis", {"role_id": world.role})
    assert analysis.error is None
    analysis_body = json.loads(analysis.output)
    assert analysis_body["score"] == result.score
    assert analysis_body["band"] == result.band
    assert {
        row["requirementId"]: row["status"] for row in analysis_body["requirements"]
    } == expected
    tool_gaps = json.loads(tools.call("get_gap_plan", {"role_id": world.role}).output)
    assert tool_gaps["currentScore"] == result.score
    assert {row["requirementId"]: row["scoreDelta"] for row in tool_gaps["items"]} == {
        row["requirementId"]: row["scoreDelta"] for row in gaps["items"]
    }
    assert accountant.records == before_calls, "result projections call no provider"
    answer = world.ask("How well do I fit this role?")
    assert f"stored_score={result.score:.0f} band={result.band}" in answer["content"]


def test_fit_gaps_ranking_ask_and_mcp_tools_reuse_the_publication(
    published: Published,
    session_factory: sessionmaker[Session],
) -> None:
    _assert_publication_consumers(published)
    bundle = published.app.client.app.state.role_store.require_analysis(
        published.workspace, published.role
    )
    assert bundle.published_result == published.result
    assert bundle.explanation.score == published.result.score
    with session_factory() as session:
        score = session.scalar(
            select(ScoreExplanationRow).where(
                ScoreExplanationRow.role_id == uuid.UUID(published.role)
            )
        )
        assert score is not None
        saved = {
            row["requirement_id"]: row
            for row in score.explanation["requirement_scores"]
        }
    for component in bundle.explanation.components:
        stored = saved[component.requirement_id]
        assert component.contribution == stored["contribution"]
        assert component.weight == stored["weight"]
    breakdown = published.app.client.get(f"/api/roles/{published.role}/breakdown")
    assert breakdown.status_code == 200


def _exercise_grounded_artifacts(
    published: Published,
) -> None:
    client, path = published.app.client, f"/api/roles/{published.role}"
    met = next(row for row in _requirements(published) if row["status"] == "met")
    pack = client.get(f"{path}/interview-pack")
    assert pack.status_code == 200, pack.text
    body = pack.json()
    assert body["provenance"]["leftMachine"] is False
    assert set(row["requirementId"] for row in body["probes"]) <= {
        item.requirement_id for item in published.result.verdicts
    }
    bullets = client.post(f"{path}/bullets", json={"requirementId": met["id"]})
    assert bullets.status_code == 200, bullets.text
    letter = client.post(
        f"{path}/cover-letter", json={"tone": "plain", "includeGapLine": False}
    )
    assert letter.status_code == 200, letter.text
    cited = set()
    for draft, parts in ((bullets.json(), "bullets"), (letter.json(), "paragraphs")):
        assert draft["provenance"]["leftMachine"] is False
        assert draft["provenance"]["grounded"] is True
        cited.update(span for part in draft[parts] for span in part["spanIds"])
    answer = published.ask("What evidence do I have for Python?")
    assert answer["citations"]
    cited.update(citation["id"] for citation in answer["citations"])
    assert cited
    for span in cited:
        evidence = client.get(f"/api/spans/{span}")
        assert evidence.status_code == 200, evidence.text
        with published.app.uow_factory() as uow:
            document = uow.documents.get(
                published.workspace, evidence.json()["documentId"]
            )
        assert document is not None
        assert evidence.json()["highlight"] in document.normalised_text
    assert client.get(f"{path}/cover-letters").json()[0]["id"] == letter.json()["id"]
    assert client.get(f"{path}/export/cover-letter.md").status_code == 200
    assert client.get(f"{path}/export/bullets.md").status_code == 200
    with published.app.uow_factory() as uow:
        assert uow.v2.result(published.workspace, published.role) == published.result
        assert uow.drafts.list_for_role(published.workspace, published.role)


def test_preparation_drafts_and_ask_citations_resolve_to_stored_evidence(
    published: Published,
) -> None:
    _exercise_grounded_artifacts(published)


def test_invalidated_publication_has_no_result_consumers_or_ranking(
    published: Published,
    session_factory: sessionmaker[Session],
) -> None:
    requirement = published.result.verdicts[0].requirement_id
    with session_factory() as session:
        score = session.scalar(
            select(ScoreExplanationRow).where(
                ScoreExplanationRow.role_id == uuid.UUID(published.role)
            )
        )
        assert score is not None
        score.invalidated = True
        session.commit()
    client, path = published.app.client, f"/api/roles/{published.role}"
    role = client.get(path).json()
    assert (role["status"], role["bandLabel"]) == ("failed", "Not scored yet")
    assert client.get("/api/ranking").json() == []
    for route in (
        "verdicts",
        "requirements",
        "breakdown",
        "gap-plan",
        "interview-pack",
    ):
        response = client.get(f"{path}/{route}")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "analysis_incomplete"
    for route, payload in (
        ("bullets", {"requirementId": requirement}),
        ("cover-letter", {"tone": "plain"}),
    ):
        assert client.post(f"{path}/{route}", json=payload).status_code == 409
    assert json.loads(published.tools().call("list_roles", {}).output)["roles"] == []
    assert (
        published.tools().call("get_role_analysis", {"role_id": published.role}).error
        == "role_not_found"
    )
    answer = client.post(
        "/api/messages",
        headers={"Accept": "application/json"},
        json={
            "content": "How well do I fit this role?",
            "roleId": published.role,
            "clientRequestId": str(uuid.uuid4()),
        },
    )
    assert answer.status_code == 409
    assert answer.json()["error"]["code"] == "analysis_incomplete"


def test_reanalysis_consumers_follow_only_the_new_publication(
    published: Published,
) -> None:
    client, role = published.app.client, published.role
    first_ids = {row.requirement_id for row in published.result.verdicts}
    new = client.post(
        "/api/cv",
        json={
            "text": "Experience\n- Completed a basic Python course.\n",
            "filename": "new-cv.txt",
        },
    )
    assert new.status_code == 201
    assert client.get(f"/api/roles/{role}/verdicts").status_code == 409
    assert client.get("/api/ranking").json() == []
    published.app.worker.drain()
    with published.app.uow_factory() as uow:
        result = uow.v2.result(published.workspace, role)
    assert result is not None and result.analysis_id != published.result.analysis_id
    assert result.score != published.result.score
    # Unchanged JD requirements keep stable identities; CV evidence must change.
    assert first_ids == {row.requirement_id for row in result.verdicts}
    old_evidence = {
        e.chunk_id for row in published.result.verdicts for e in row.evidence
    }
    new_evidence = {e.chunk_id for row in result.verdicts for e in row.evidence}
    assert not old_evidence & new_evidence
    with published.app.uow_factory() as uow:
        assert uow.chunks.load_chunks(published.workspace, tuple(old_evidence)) == ()
    _assert_publication_consumers(Published(published.app, role, result))


def _workspace_counts(factory: sessionmaker[Session], workspace: str) -> dict[str, int]:
    with factory() as session:
        return {
            table.name: len(
                session.execute(
                    select(table.c.workspace_id).where(
                        table.c.workspace_id == uuid.UUID(workspace)
                    )
                ).all()
            )
            for table in Base.metadata.sorted_tables
            if "workspace_id" in table.c
        }


def test_populated_workspace_deletion_is_complete_and_scoped(
    published: Published,
    session_factory: sessionmaker[Session],
) -> None:
    _exercise_grounded_artifacts(published)
    published.ask("How did I describe my warehouse work?")
    other = sql_app(session_factory)
    other_role, _ = analyse(other)
    other_workspace = other.client.cookies["workspace"]
    counts = _workspace_counts(session_factory, published.workspace)
    assert all(
        counts[table] > 0
        for table in (
            "documents",
            "spans",
            "chunks",
            "chunk_embeddings",
            "requirement_items",
            "match_verdicts",
            "verdict_evidence",
            "retrieval_traces",
            "score_explanations",
            "generated_drafts",
            "draft_citations",
            "conversations",
            "questions",
            "answers",
            "answer_citations",
            "provider_call_accounting",
            "analysis_jobs",
            "analysis_job_tasks",
        )
    )
    before = _workspace_counts(session_factory, other_workspace)
    with session_factory() as session:
        session.execute(
            delete(WorkspaceRow).where(
                WorkspaceRow.id == uuid.UUID(published.workspace)
            )
        )
        session.commit()
        assert session.get(WorkspaceRow, uuid.UUID(published.workspace)) is None
    assert not any(_workspace_counts(session_factory, published.workspace).values())
    assert _workspace_counts(session_factory, other_workspace) == before
    assert other.client.get(f"/api/roles/{other_role}/verdicts").status_code == 200
