"""Provider catalogue and workspace provider-choice routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from career_assistant.adapters.providers.factory import build_egress_policy
from career_assistant.api.deps import WorkspaceId
from career_assistant.api.errors import AppError
from career_assistant.api.schemas import (
    ProviderCapabilitiesModel,
    ProviderChoiceResponse,
    ProviderChoiceUpdateRequest,
    ProviderResponse,
    ProviderSupportsModel,
)
from career_assistant.application.providers.catalogue import (
    ProviderChoice,
    ProviderSelectionRejected,
    apply_provider_choice,
    default_provider_choice,
    list_provider_catalogue,
)
from career_assistant.settings import ProviderSettings

router = APIRouter(tags=["providers"])


def _settings(request: Request) -> ProviderSettings:
    configured = getattr(request.app.state, "providers", None)
    if isinstance(configured, ProviderSettings):
        return configured
    return ProviderSettings()


def _choice_store(request: Request) -> dict[str, ProviderChoice]:
    store = getattr(request.app.state, "provider_choices", None)
    if store is None:
        store = {}
        request.app.state.provider_choices = store
    return store


def _to_response(choice: ProviderChoice) -> ProviderChoiceResponse:
    return ProviderChoiceResponse(
        answer_provider_id=choice.answer_provider_id,
        answer_model=choice.answer_model,
        index_provider_id=choice.index_provider_id,
        index_model=choice.index_model,
    )


@router.get("/providers", response_model=list[ProviderResponse])
def get_providers(request: Request) -> list[ProviderResponse]:
    settings = _settings(request)
    egress = build_egress_policy(settings)
    return [
        ProviderResponse(
            id=item.id,
            name=item.name,
            kind=item.kind,
            models=list(item.models),
            available=item.available,
            unavailable_reason=item.unavailable_reason,
            supports=ProviderSupportsModel(
                completion=item.supports.completion,
                embedding=item.supports.embedding,
            ),
            capabilities=ProviderCapabilitiesModel(
                structured_output=item.capabilities.structured_output,
                context_window=item.capabilities.context_window,
                max_output_tokens=item.capabilities.max_output_tokens,
                embedding_dimensions=item.capabilities.embedding_dimensions,
            ),
        )
        for item in list_provider_catalogue(settings, egress)
    ]


@router.get("/settings/providers", response_model=ProviderChoiceResponse)
def get_provider_choice(
    request: Request, workspace_id: WorkspaceId
) -> ProviderChoiceResponse:
    store = _choice_store(request)
    choice = store.get(workspace_id) or default_provider_choice(_settings(request))
    return _to_response(choice)


@router.put("/settings/providers", response_model=ProviderChoiceResponse)
def put_provider_choice(
    request: Request,
    body: ProviderChoiceUpdateRequest,
    workspace_id: WorkspaceId,
) -> ProviderChoiceResponse:
    settings = _settings(request)
    egress = build_egress_policy(settings)
    proposed = ProviderChoice(
        answer_provider_id=body.answer_provider_id,
        answer_model=body.answer_model,
        index_provider_id=body.index_provider_id,
        index_model=body.index_model,
    )
    try:
        applied = apply_provider_choice(
            settings,
            egress,
            choice=proposed,
            acknowledged_egress=body.acknowledged_egress,
        )
    except ProviderSelectionRejected as exc:
        raise AppError(exc.code, exc.message, status_code=exc.status_code) from exc
    _choice_store(request)[workspace_id] = applied
    return _to_response(applied)
