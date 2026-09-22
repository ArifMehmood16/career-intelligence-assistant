"""Ask / message routes — SSE and JSON share AskService."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import StreamingResponse

from career_assistant.api.deps import WorkspaceId
from career_assistant.api.errors import AppError
from career_assistant.api.provider_runtime import completion_port_for
from career_assistant.api.schemas import (
    ChatMessageWire,
    CitationWire,
    MessageCreateRequest,
)
from career_assistant.api.sse import format_ask_sse
from career_assistant.application.ask.memory import (
    InMemoryConversationStore,
    MemoryMessage,
)
from career_assistant.application.ask.service import (
    AskRequest,
    AskService,
    ConversationStore,
)
from career_assistant.application.ask.views import role_analysis_view
from career_assistant.application.documents.cv import CvStore, InMemoryCvStore
from career_assistant.application.documents.supporting import (
    InMemorySupportingDocumentStore,
    SupportingDocumentStore,
)
from career_assistant.application.intake.workspace_spans import retrieval_pool
from career_assistant.application.roles.store import (
    InMemoryRoleStore,
    RoleOperationRejected,
    RoleView,
)
from career_assistant.domain.ask import AnswerResult, RoleAnalysisView
from career_assistant.domain.prompts import RetrievedSpan
from career_assistant.settings import LimitSettings, ProviderSettings

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


def _supporting_store(request: Request) -> SupportingDocumentStore:
    store = getattr(request.app.state, "supporting_store", None)
    if store is None:
        store = InMemorySupportingDocumentStore(cv_store=_cv_store(request))
        request.app.state.supporting_store = store
    return store


def _conversation_store(request: Request) -> ConversationStore:
    store = getattr(request.app.state, "conversation_store", None)
    if store is None:
        store = InMemoryConversationStore()
        request.app.state.conversation_store = store
    return store


def _view_for_role(
    store: InMemoryRoleStore, workspace_id: str, role: RoleView
) -> RoleAnalysisView:
    try:
        bundle = store.require_analysis(workspace_id, role.id)
    except RoleOperationRejected as exc:
        raise AppError(exc.code, exc.message, status_code=exc.status_code) from exc
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
    ids: set[str] = {item.span.id for item in _retrieved_pool(request, workspace_id)}
    for role in roles:
        ids.update(role.span_texts)
    return frozenset(ids)


def _retrieved_pool(request: Request, workspace_id: str) -> tuple[RetrievedSpan, ...]:
    return retrieval_pool(
        workspace_id,
        cv_store=_cv_store(request),
        supporting_store=_supporting_store(request),
        role_store=_role_store(request),
    )


def _ask_service(
    request: Request,
    workspace_id: str,
    roles: tuple[RoleAnalysisView, ...],
) -> AskService:
    providers = getattr(request.app.state, "providers", None)
    output_limit = (
        providers.llm_max_output_tokens
        if isinstance(providers, ProviderSettings)
        else 2000
    )
    limits = getattr(request.app.state, "limits", None)
    if not isinstance(limits, LimitSettings):
        limits = LimitSettings(_env_file=None)
    return AskService(
        store=_conversation_store(request),
        completion=completion_port_for(request, workspace_id),
        known_span_ids=_known_span_ids(request, workspace_id, roles),
        id_factory=lambda _prefix: str(uuid.uuid4()),
        output_token_limit=output_limit,
        max_question_chars=limits.max_question_chars,
        max_context_chars=limits.max_context_chars,
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


def _as_memory_message(message: object) -> MemoryMessage:
    if isinstance(message, MemoryMessage):
        return message
    raise TypeError("conversation store must yield MemoryMessage records")


def _citations_wire(result: AnswerResult) -> list[CitationWire]:
    return [
        CitationWire(id=citation.span_id, label=citation.label, evidence=None)
        for citation in result.citations
    ]


def _assistant_message_wire(
    *,
    result: AnswerResult,
    answer: MemoryMessage,
) -> ChatMessageWire:
    created = answer.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return ChatMessageWire(
        id=answer.id,
        conversation_id=answer.conversation_id,
        author="assistant",
        content=result.content,
        kind=result.kind.value,
        citations=_citations_wire(result),
        model=answer.model,
        provider=answer.provider,
        left_machine=answer.left_machine,
        created_at=created.isoformat().replace("+00:00", "Z"),
    )


def _history_message_wire(message: MemoryMessage) -> ChatMessageWire:
    created = message.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return ChatMessageWire(
        id=message.id,
        conversation_id=message.conversation_id,
        author=message.author,
        content=message.content,
        kind=message.kind,
        citations=[
            CitationWire(id=span_id, label=span_id, evidence=None)
            for span_id in message.citations
        ],
        model=message.model,
        provider=message.provider,
        left_machine=message.left_machine,
        created_at=created.isoformat().replace("+00:00", "Z"),
    )


@router.get("/messages", response_model=list[ChatMessageWire])
def get_messages(request: Request, workspace_id: WorkspaceId) -> list[ChatMessageWire]:
    store = _conversation_store(request)
    conversation_id = store.conversation_id_for(workspace_id)
    if conversation_id is None:
        return []
    history = store.list_history(workspace_id, conversation_id)
    return [_history_message_wire(_as_memory_message(message)) for message in history]


@router.delete(
    "/messages",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_messages(request: Request, workspace_id: WorkspaceId) -> Response:
    store = _conversation_store(request)
    conversation_id = store.conversation_id_for(workspace_id)
    if conversation_id is not None:
        store.hard_delete(workspace_id, conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/messages", response_model=ChatMessageWire)
def post_message(
    request: Request,
    workspace_id: WorkspaceId,
    body: MessageCreateRequest,
) -> ChatMessageWire | StreamingResponse:
    """Ask via SSE or JSON — both paths share AskService."""
    accept = request.headers.get("accept", "")
    roles = _roles_for_ask(request, workspace_id, body.role_id)
    ask_request = _build_ask_request(request, workspace_id, body, roles)
    service = _ask_service(request, workspace_id, roles)

    if "text/event-stream" in accept:

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

    if "application/json" not in accept and "*/*" not in accept and accept.strip():
        raise AppError(
            "validation_failed",
            "Accept must be text/event-stream or application/json.",
            status_code=406,
        )

    result = service.ask(ask_request)
    found = _conversation_store(request).find_by_client_request_id(
        workspace_id, ask_request.client_request_id
    )
    if found is None:
        raise AppError(
            "internal_error",
            "Answer was not persisted.",
            status_code=500,
        )
    _question, answer = found
    return _assistant_message_wire(result=result, answer=_as_memory_message(answer))
