"""Workspace matching-pipeline setting (PLAN 18.10)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from career_assistant.api.deps import WorkspaceId
from career_assistant.api.schemas import PipelineSetting
from career_assistant.application.pipeline_store import PipelineVersionStore

router = APIRouter(tags=["settings"])


def _store(request: Request) -> PipelineVersionStore:
    store: PipelineVersionStore = request.app.state.pipeline_store
    return store


@router.get("/settings/pipeline", response_model=PipelineSetting)
def get_pipeline(request: Request, workspace_id: WorkspaceId) -> PipelineSetting:
    return PipelineSetting(pipeline_version=_store(request).get(workspace_id))


@router.put("/settings/pipeline", response_model=PipelineSetting)
def put_pipeline(
    request: Request, body: PipelineSetting, workspace_id: WorkspaceId
) -> PipelineSetting:
    _store(request).put(workspace_id, body.pipeline_version)
    return PipelineSetting(pipeline_version=_store(request).get(workspace_id))
