"""Ask / message routes — SSE and JSON share AskService."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from career_assistant.adapters.providers.hermetic.completion import (
    HermeticCompletionAdapter,
)
from career_assistant.api.deps import WorkspaceId
from career_assistant.api.errors import AppError
from career_assistant.api.schemas import MessageCreateRequest
from career_assistant.api.sse import format_ask_sse
from career_assistant.application.ask.memory import InMemoryConversationStore
from career_assistant.application.ask.service import AskRequest, AskService
from career_assistant.application.ask.views import role_analysis_view
from career_assistant.application.documents.cv import CvStore, InMemoryCvStore
from career_assistant.application.roles.store import InMemoryRoleStore, RoleView
from career_assistant.domain.ask import RoleAnalysisView
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.prompts import RetrievedSpan

router = APIRouter(tags=["ask"])


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


def _conversation_store(request: Request) -> InMemoryConversationStore:
    store = getattr(request.app.state, "conversation_store", None)
    if store is None:
        store = InMemoryConversationStore()
        request.app.state.conversation_store = store
    return store


def _view_for_role(
    store: InMemoryRoleStore, workspace_id: str, role: RoleView
) -> RoleAnalysisView:
    bundle = store.require_analysis(workspace_id, role.id)
    return role_analysis_view(role_id=role.id, title=role.title, bundle=bundle)


def _roles_for_ask(
    request: Request, workspace_id: str, role_id: str | None
) -> tuple[RoleAnalysisView, ...]:
    store = _role_store(request)
    if role_id is not None:
        role = store.get_role(workspace_id, role_id)
        if role is None:
            raise AppError("role_not_found", "No role with that id.", status_code=404)
        return (_view_for_role(store, workspace_id, role),)
    roles = store.list_roles(workspace_id)
    return tuple(_view_for_role(store, workspace_id, role) for role in roles)


def _known_span_ids(
    request: Request,
    workspace_id: str,
    roles: tuple[RoleAnalysisView, ...],
) -> frozenset[str]:
    ids: set[str] = set()
    cv = _cv_store(request).get_active(workspace_id)
    if cv is not None:
        ids.update(span.id for span in cv.spans)
    for role in roles:
        ids.update(role.span_texts)
    return frozenset(ids)


def _retrieved_pool(request: Request, workspace_id: str) -> tuple[RetrievedSpan, ...]:
    cv = _cv_store(request).get_active(workspace_id)
    if cv is None:
        return ()
    return tuple(
        RetrievedSpan(span=span, document_kind=DocumentKind.CV) for span in cv.spans
    )


def _ask_service(
    request: Request,
    workspace_id: str,
    roles: tuple[RoleAnalysisView, ...],
) -> AskService:
    return AskService(
        store=_conversation_store(request),
        completion=HermeticCompletionAdapter(),
        known_span_ids=_known_span_ids(request, workspace_id, roles),
        id_factory=lambda _prefix: str(uuid.uuid4()),
    )


def _build_ask_request(
    request: Request,
    workspace_id: str,
    body: MessageCreateRequest,
    roles: tuple[RoleAnalysisView, ...],
) -> AskRequest:
    if not body.content.strip():
        raise AppError(
            "validation_failed", "Message content is required.", status_code=422
        )
    if not body.client_request_id.strip():
        raise AppError(
            "validation_failed",
            "clientRequestId is required.",
            status_code=422,
        )
    conversation_id = _conversation_store(request).ensure_conversation(workspace_id)
    return AskRequest(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        client_request_id=body.client_request_id.strip(),
        content=body.content.strip(),
        role_id=body.role_id,
        roles=roles,
        retrieved_pool=_retrieved_pool(request, workspace_id),
    )


@router.post("/messages", response_class=StreamingResponse)
def post_message(
    request: Request,
    workspace_id: WorkspaceId,
    body: MessageCreateRequest,
) -> StreamingResponse:
    """Stream the ask event sequence when Accept prefers text/event-stream."""
    accept = request.headers.get("accept", "")
    if "text/event-stream" not in accept:
        raise AppError(
            "validation_failed",
            "Accept: text/event-stream is required for this slice.",
            status_code=406,
        )
    roles = _roles_for_ask(request, workspace_id, body.role_id)
    ask_request = _build_ask_request(request, workspace_id, body, roles)
    service = _ask_service(request, workspace_id, roles)

    def event_stream() -> Iterator[str]:
        for event in service.stream(ask_request):
            yield format_ask_sse(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
