"""Resolve the workspace completion port for Ask and generation routes."""

from __future__ import annotations

from fastapi import Request

from career_assistant.adapters.providers.factory import (
    build_completion_port,
    build_tool_calling_port,
)
from career_assistant.api.errors import AppError
from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.errors import (
    EgressNotPermittedError,
    ProviderUnavailableError,
)
from career_assistant.application.ports.tool_calling import (
    ToolCallingPort,
    ToolCallingRequest,
    ToolCallingResult,
)
from career_assistant.application.ports.types import (
    CallRecord,
    CapabilityDescriptor,
)
from career_assistant.application.providers.accounting import (
    AccountingCompletion,
    CallAccountant,
)
from career_assistant.application.providers.catalogue import default_provider_choice
from career_assistant.application.providers.choice_store import (
    InMemoryProviderChoiceStore,
    ProviderChoiceStore,
)
from career_assistant.settings import ProviderSettings


def provider_settings(request: Request) -> ProviderSettings:
    configured = getattr(request.app.state, "providers", None)
    if isinstance(configured, ProviderSettings):
        return configured
    return ProviderSettings(
        completion_provider="hermetic",
        embedding_provider="hermetic",
    )


def choice_store(request: Request) -> ProviderChoiceStore:
    store = getattr(request.app.state, "provider_choice_store", None)
    if store is None:
        store = InMemoryProviderChoiceStore()
        request.app.state.provider_choice_store = store
    return store


def completion_port_for(request: Request, workspace_id: str) -> CompletionPort:
    settings = provider_settings(request)
    choice = choice_store(request).get(workspace_id) or default_provider_choice(
        settings
    )
    transport = getattr(request.app.state, "http_transport", None)
    try:
        port = build_completion_port(
            settings,
            transport=transport,
            provider_id=choice.answer_provider_id,
            model_tag=choice.answer_model,
        )
    except EgressNotPermittedError as exc:
        raise AppError(
            "egress_not_permitted",
            "Hosted provider is not permitted.",
            status_code=403,
        ) from exc
    accountant = getattr(request.app.state, "call_accountant", None)
    if accountant is None:
        accountant = CallAccountant()
        request.app.state.call_accountant = accountant
    return AccountingCompletion(
        port,
        accountant,
        workspace_id=workspace_id,
        purpose="complete",
    )


def tool_calling_port_for(
    request: Request, workspace_id: str
) -> ToolCallingPort | None:
    """The answer model's tool caller, or None when it cannot be built."""
    settings = provider_settings(request)
    choice = choice_store(request).get(workspace_id) or default_provider_choice(
        settings
    )
    transport = getattr(request.app.state, "http_transport", None)
    try:
        port = build_tool_calling_port(
            settings,
            transport=transport,
            provider_id=choice.answer_provider_id,
            model_tag=choice.answer_model,
        )
    except EgressNotPermittedError, ProviderUnavailableError:
        return None
    accountant = getattr(request.app.state, "call_accountant", None)
    if not isinstance(accountant, CallAccountant):
        accountant = CallAccountant()
    return _AccountedToolCalling(port, accountant, workspace_id=workspace_id)


class _AccountedToolCalling:
    """Records provider and token counts for a tool turn, never the text."""

    def __init__(
        self,
        inner: ToolCallingPort,
        accountant: CallAccountant,
        *,
        workspace_id: str,
    ) -> None:
        self._inner = inner
        self._accountant = accountant
        self._workspace_id = workspace_id

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete(self, request: ToolCallingRequest) -> ToolCallingResult:
        result = self._inner.complete(request)
        self._accountant.record(
            CallRecord(
                provider_id=result.provider_id,
                model_tag=result.model_tag,
                operation="tool_calling",
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                latency_ms=None,
                estimated_cost_usd=None,
                left_machine=result.left_machine,
                metadata={"workspace_id": self._workspace_id, "purpose": "ask"},
            )
        )
        return result
