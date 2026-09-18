"""Span evidence routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from career_assistant.api.deps import WorkspaceId
from career_assistant.api.errors import AppError
from career_assistant.api.schemas import EvidenceResponse
from career_assistant.application.documents.cv import CvStore, InMemoryCvStore
from career_assistant.application.intake.resolve_span import (
    SpanNotFoundError,
    resolve_span,
)
from career_assistant.domain.documents import Evidence

router = APIRouter(tags=["spans"])


def _store(request: Request) -> CvStore:
    store = getattr(request.app.state, "cv_store", None)
    if store is None:
        store = InMemoryCvStore()
        request.app.state.cv_store = store
    return store


@router.get("/spans/{span_id}", response_model=EvidenceResponse)
def get_span(
    span_id: str, request: Request, workspace_id: WorkspaceId
) -> EvidenceResponse:
    found = _store(request).get_span(workspace_id, span_id)
    if found is None:
        raise AppError("span_not_found", "No span with that id.", status_code=404)
    span, pages = found
    try:
        evidence: Evidence = resolve_span(span, pages)
    except SpanNotFoundError as exc:
        raise AppError(
            "span_not_found", "No span with that id.", status_code=404
        ) from exc
    return EvidenceResponse(
        span_id=span.id,
        document_id=evidence.document_id,
        page=evidence.page,
        paragraph=evidence.paragraph,
        highlight=evidence.highlight,
    )
