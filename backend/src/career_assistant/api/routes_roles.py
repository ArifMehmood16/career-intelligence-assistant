"""Role and analysis-job routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from career_assistant.api.deps import WorkspaceId
from career_assistant.api.errors import AppError
from career_assistant.api.schemas import (
    AnalysisJobResponse,
    ReanalyseResponse,
    RoleCounts,
    RoleCreatedResponse,
    RoleCreateRequest,
    RoleResponse,
)
from career_assistant.application.documents.cv import CvStore, InMemoryCvStore
from career_assistant.application.roles.store import (
    InMemoryRoleStore,
    JobView,
    RoleOperationRejected,
    RoleView,
)

router = APIRouter(tags=["roles"])


def _cv_store(request: Request) -> CvStore:
    store = getattr(request.app.state, "cv_store", None)
    if store is None:
        store = InMemoryCvStore()
        request.app.state.cv_store = store
    return store


def _role_store(request: Request) -> InMemoryRoleStore:
    store = getattr(request.app.state, "role_store", None)
    if store is None:
        store = InMemoryRoleStore(cv_store=_cv_store(request))
        request.app.state.role_store = store
    return store


def _role_response(role: RoleView) -> RoleResponse:
    return RoleResponse(
        id=role.id,
        title=role.title,
        company=role.company,
        fit_score=role.fit_score,
        band_label=role.band_label,
        counts=RoleCounts(**role.counts),
        status=role.status,
        updated_at=role.updated_at.isoformat().replace("+00:00", "Z"),
    )


def _job_response(job: JobView) -> AnalysisJobResponse:
    return AnalysisJobResponse(
        id=job.id,
        kind=job.kind,
        state=job.state,
        stage=job.stage,
        started_at=(
            None
            if job.started_at is None
            else job.started_at.isoformat().replace("+00:00", "Z")
        ),
        finished_at=(
            None
            if job.finished_at is None
            else job.finished_at.isoformat().replace("+00:00", "Z")
        ),
        error=job.error,
    )


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(request: Request, workspace_id: WorkspaceId) -> list[RoleResponse]:
    roles = _role_store(request).list_roles(workspace_id)
    return [_role_response(role) for role in roles]


@router.post(
    "/roles",
    response_model=RoleCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_role(
    request: Request,
    body: RoleCreateRequest,
    workspace_id: WorkspaceId,
) -> RoleCreatedResponse:
    try:
        role, job = _role_store(request).create_role(
            workspace_id=workspace_id,
            title=body.title,
            company=body.company,
            description=body.description,
        )
    except RoleOperationRejected as exc:
        raise AppError(exc.code, exc.message, status_code=exc.status_code) from exc
    return RoleCreatedResponse(role=_role_response(role), job_id=job.id)


@router.get("/roles/{role_id}", response_model=RoleResponse)
def get_role(role_id: str, request: Request, workspace_id: WorkspaceId) -> RoleResponse:
    role = _role_store(request).get_role(workspace_id, role_id)
    if role is None:
        raise AppError("role_not_found", "No role with that id.", status_code=404)
    return _role_response(role)


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_role(role_id: str, request: Request, workspace_id: WorkspaceId) -> None:
    try:
        _role_store(request).delete_role(workspace_id, role_id)
    except RoleOperationRejected as exc:
        raise AppError(exc.code, exc.message, status_code=exc.status_code) from exc


@router.post(
    "/roles/{role_id}/reanalyse",
    response_model=ReanalyseResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def reanalyse_role(
    role_id: str, request: Request, workspace_id: WorkspaceId
) -> ReanalyseResponse:
    try:
        _role, job = _role_store(request).reanalyse(workspace_id, role_id)
    except RoleOperationRejected as exc:
        raise AppError(exc.code, exc.message, status_code=exc.status_code) from exc
    return ReanalyseResponse(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=AnalysisJobResponse)
def get_job(
    job_id: str, request: Request, workspace_id: WorkspaceId
) -> AnalysisJobResponse:
    job = _role_store(request).get_job(workspace_id, job_id)
    if job is None:
        raise AppError("role_not_found", "No job with that id.", status_code=404)
    return _job_response(job)
