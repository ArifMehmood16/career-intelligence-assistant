"""Supporting cover-letter and document-download routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import Response as StarletteResponse

from career_assistant.api.deps import WorkspaceId
from career_assistant.api.errors import AppError
from career_assistant.api.schemas import CvPasteRequest, SupportingDocumentResponse
from career_assistant.application.documents.cv import CvStore, InMemoryCvStore
from career_assistant.application.documents.supporting import (
    InMemorySupportingDocumentStore,
    SupportingDocumentStore,
    SupportingDocumentView,
    limits_from,
    reraise_intake_as_message,
    upload_pasted_cover_letter,
)
from career_assistant.application.intake.errors import IntakeError
from career_assistant.settings import LimitSettings

router = APIRouter(tags=["documents"])


def _cv_store(request: Request) -> CvStore:
    store = getattr(request.app.state, "cv_store", None)
    if store is None:
        store = InMemoryCvStore()
        request.app.state.cv_store = store
    return store


def _supporting_store(request: Request) -> SupportingDocumentStore:
    store = getattr(request.app.state, "supporting_store", None)
    if store is None:
        store = InMemorySupportingDocumentStore(cv_store=_cv_store(request))
        request.app.state.supporting_store = store
    return store


def _limits(request: Request) -> LimitSettings:
    configured = getattr(request.app.state, "limits", None)
    if isinstance(configured, LimitSettings):
        return configured
    return LimitSettings()


def _to_response(view: SupportingDocumentView) -> SupportingDocumentResponse:
    return SupportingDocumentResponse(
        id=view.id,
        kind=view.kind,
        filename=view.filename,
        media_type=view.media_type,
        byte_length=view.byte_length,
        page_count=view.page_count,
        parsed_at=view.parsed_at.isoformat().replace("+00:00", "Z"),
        created_at=view.created_at.isoformat().replace("+00:00", "Z"),
    )


@router.get("/cover-letters", response_model=list[SupportingDocumentResponse])
def list_cover_letters(
    request: Request, workspace_id: WorkspaceId
) -> list[SupportingDocumentResponse]:
    return [
        _to_response(view)
        for view in _supporting_store(request).list_cover_letters(workspace_id)
    ]


@router.post(
    "/cover-letters",
    response_model=SupportingDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_cover_letter(
    request: Request,
    body: CvPasteRequest,
    workspace_id: WorkspaceId,
) -> SupportingDocumentResponse:
    try:
        view = upload_pasted_cover_letter(
            _supporting_store(request),
            workspace_id=workspace_id,
            text=body.text,
            filename=body.filename,
            limits=limits_from(_limits(request)),
        )
    except IntakeError as exc:
        code, message, http_status = reraise_intake_as_message(exc)
        raise AppError(code, message, status_code=http_status) from exc
    return _to_response(view)


@router.delete(
    "/cover-letters/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_cover_letter(
    document_id: str, request: Request, workspace_id: WorkspaceId
) -> Response:
    deleted = _supporting_store(request).delete_cover_letter(workspace_id, document_id)
    if not deleted:
        raise AppError(
            "cover_letter_not_found",
            "No cover letter with that id.",
            status_code=404,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/documents/{document_id}/download",
    response_model=None,
    response_class=Response,
)
def download_document(
    document_id: str, request: Request, workspace_id: WorkspaceId
) -> StarletteResponse:
    found = _supporting_store(request).get_downloadable(workspace_id, document_id)
    if found is None:
        raise AppError(
            "cover_letter_not_found",
            "No document with that id in this workspace.",
            status_code=404,
        )
    # Safe Content-Disposition: basename only, no paths.
    safe_name = found.filename.replace('"', "").replace("/", "_").replace("\\", "_")
    return StarletteResponse(
        content=found.original_bytes,
        media_type=found.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
        },
    )
