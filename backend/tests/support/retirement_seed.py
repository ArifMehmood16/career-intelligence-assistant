"""Synthetic historical rows for the populated retirement upgrade regression."""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.support.v2_seed import insert_row


@dataclass(frozen=True)
class HistoricalRole:
    role: str
    job: str


def historical_job(
    session: Session, workspace: str, role: str, *, state: str, pipeline: str
) -> str:
    job = insert_row(
        session,
        "analysis_jobs",
        workspace_id=workspace,
        role_id=role,
        kind="role_analysis",
        state=state,
        stage="mapping" if state == "running" else None,
        pipeline_version=pipeline,
    )
    # Historical progress uses no provider/client objects or document content.
    session.execute(
        text(
            "INSERT INTO career_assistant.analysis_job_tasks "
            "(job_id, workspace_id, key, position, state) "
            "VALUES (:job, :ws, 'judge', 0, :state)"
        ),
        {
            "job": job,
            "ws": workspace,
            "state": "running" if state == "running" else "pending",
        },
    )
    return job


def historical_score(
    session: Session,
    workspace: str,
    role: str,
    span: str,
    *,
    version: int = 1,
    pipeline: str | None = "v1",
) -> str:
    payload = {} if pipeline is None else {"pipeline_version": pipeline}
    insert_row(
        session,
        "score_explanations",
        workspace_id=workspace,
        role_id=role,
        analysis_version=version,
        score=88.0,
        band="strong",
        explanation=json.dumps(payload),
        invalidated=False,
    )
    draft = insert_row(
        session,
        "generated_drafts",
        workspace_id=workspace,
        role_id=role,
        kind="bullets",
        body="Synthetic historical draft.",
        analysis_version=version,
        version=version + 100,
        provider="hermetic",
        model_tag="rules-v1",
        left_machine=False,
        groundedness="pass",
        used_template_fallback=True,
        regeneration_count=0,
    )
    insert_row(
        session, "draft_citations", workspace_id=workspace, draft_id=draft, span_id=span
    )
    return draft


def historical_role(
    session: Session,
    workspace: str,
    jd: str,
    *,
    state: str,
    pipeline: str = "v1",
) -> HistoricalRole:
    role = insert_row(
        session,
        "roles",
        workspace_id=workspace,
        title=f"Synthetic {pipeline} {state}",
        company="Synthetic",
        job_description_document_id=jd,
        analysis_version=1,
        status="ready" if state == "succeeded" else "analysing",
    )
    return HistoricalRole(
        role, historical_job(session, workspace, role, state=state, pipeline=pipeline)
    )
