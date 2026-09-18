"""CV HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from career_assistant.api.deps import WorkspaceId
from career_assistant.api.errors import AppError
from career_assistant.api.schemas import (
    CvDocumentResponse,
    CvPasteRequest,
    CvUploadResponse,
    ReanalysisInfo,
)
from career_assistant.application.documents.cv import (
    CvStore,
    InMemoryCvStore,
    admission_limits_from,
    delete_cv,
    get_cv,
    reraise_intake_as_message,
    upload_pasted_cv,
)
from career_assistant.application.intake.errors import IntakeError
from career_assistant.settings import LimitSettings

router = APIRouter(tags=["cv"])


def _store(request: Request) -> CvStore:
    store = getattr(request.app.state, "cv_store", None)
    if store is None:
        store = InMemoryCvStore()
        request.app.state.cv_store = store
    return store


def _limits(request: Request) -> LimitSettings:
    configured = getattr(request.app.state, "limits", None)
    if isinstance(configured, LimitSettings):
        return configured
    return LimitSettings()


def _to_response(view: object) -> CvDocumentResponse:
    from career_assistant.application.documents.cv import CvView

    assert isinstance(view, CvView)
    return CvDocumentResponse(
        id=view.id,
        filename=view.filename,
        page_count=view.page_count,
        parsed_at=view.parsed_at.isoformat().replace("+00:00", "Z"),
    )


@router.get("/cv", response_model=CvDocumentResponse | None)
def get_active_cv(
    request: Request, workspace_id: WorkspaceId
) -> CvDocumentResponse | None:
    view = get_cv(_store(request), workspace_id=workspace_id)
    if view is None:
        return None
    return _to_response(view)


@router.post(
    "/cv",
    response_model=CvUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_cv(
    request: Request,
    body: CvPasteRequest,
    workspace_id: WorkspaceId,
) -> CvUploadResponse:
    try:
        view = upload_pasted_cv(
            _store(request),
            workspace_id=workspace_id,
            text=body.text,
            filename=body.filename,
            limits=admission_limits_from(_limits(request)),
        )
    except IntakeError as exc:
        code, message, http_status = reraise_intake_as_message(exc)
        raise AppError(code, message, status_code=http_status) from exc
    return CvUploadResponse(
        id=view.id,
        filename=view.filename,
        page_count=view.page_count,
        parsed_at=view.parsed_at.isoformat().replace("+00:00", "Z"),
        reanalysis=ReanalysisInfo(job_ids=list(view.reanalysis_job_ids)),
    )


@router.delete("/cv", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def remove_cv(request: Request, workspace_id: WorkspaceId) -> Response:
    delete_cv(_store(request), workspace_id=workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
