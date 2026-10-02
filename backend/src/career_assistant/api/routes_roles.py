"""Role and analysis-job routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from career_assistant.adapters.providers.hermetic.analysis import analyse_hermetic
from career_assistant.api.deps import WorkspaceId
from career_assistant.api.errors import AppError
from career_assistant.api.schemas import (
    AnalysisJobResponse,
    JobErrorBody,
    JobProgressWire,
    JobTaskWire,
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
from career_assistant.domain.generation import build_fit_summary
from career_assistant.domain.progress import ProgressView

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
        store = InMemoryRoleStore(
            cv_store=_cv_store(request), analyser=analyse_hermetic
        )
        request.app.state.role_store = store
    return store


def _role_response(role: RoleView, *, fit_summary: str | None = None) -> RoleResponse:
    return RoleResponse(
        id=role.id,
        title=role.title,
        company=role.company,
        fit_score=role.fit_score,
        band_label=role.band_label,
        counts=RoleCounts(**role.counts),
        status=role.status,
        updated_at=role.updated_at.isoformat().replace("+00:00", "Z"),
        fit_summary=fit_summary,
        active_job=_job_response(role.active_job) if role.active_job else None,
        analysis_pipeline=role.analysis_pipeline,
    )


def _fit_summary_for(
    store: InMemoryRoleStore, workspace_id: str, role: RoleView
) -> str | None:
    if role.status != "ready":
        return None
    try:
        bundle = store.require_analysis(workspace_id, role.id)
    except RoleOperationRejected:
        return None
    return build_fit_summary(
        bundle.requirements,
        bundle.mappings,
        explanation=bundle.explanation,
        gaps=bundle.gaps,
    ).text


def _job_response(job: JobView) -> AnalysisJobResponse:
    error = None
    if job.error is not None:
        error = JobErrorBody(code=job.error.code, message=job.error.message)
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
        error=error,
        progress=_progress_wire(job.progress) if job.progress else None,
    )


def _progress_wire(view: ProgressView) -> JobProgressWire:
    return JobProgressWire(
        tasks_done=view.tasks_done,
        tasks_total=view.tasks_total,
        fraction=round(view.fraction, 4),
        current_task=view.current.value if view.current is not None else None,
        elapsed_seconds=_whole_seconds(view.elapsed_seconds),
        remaining_seconds=_whole_seconds(view.remaining_seconds),
        queue_position=view.queue_position,
        model_calls_done=view.model_calls_done,
        model_calls_remaining=view.model_calls_remaining,
        embedding_calls_done=view.embedding_calls_done,
        embedding_calls_remaining=view.embedding_calls_remaining,
        call_estimate_complete=view.call_estimate_complete,
        tasks=[
            JobTaskWire(
                key=task.key.value,
                state=task.state.value,
                units_done=task.units_done,
                units_total=task.units_total,
                model_calls_done=task.model_calls_done,
                model_calls_total=task.model_calls_total,
                embedding_calls_done=task.embedding_calls_done,
                embedding_calls_total=task.embedding_calls_total,
            )
            for task in view.tasks
        ],
    )


def _whole_seconds(seconds: float | None) -> int | None:
    return None if seconds is None else round(seconds)


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
    store = _role_store(request)
    role = store.get_role(workspace_id, role_id)
    if role is None:
        raise AppError("role_not_found", "No role with that id.", status_code=404)
    return _role_response(role, fit_summary=_fit_summary_for(store, workspace_id, role))


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
