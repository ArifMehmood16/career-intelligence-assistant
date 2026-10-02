"""Composition root for completion and embedding adapters."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from career_assistant.adapters.providers.anthropic import builders as anthropic
from career_assistant.adapters.providers.construction import ProviderConstruction
from career_assistant.adapters.providers.hermetic import builders as hermetic
from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.providers.httpx_transport import HttpxTransport
from career_assistant.adapters.providers.ollama import builders as ollama
from career_assistant.adapters.providers.openai import builders as openai
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
)
from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.errors import ProviderUnavailableError
from career_assistant.application.ports.tool_calling import (
    ToolCallingPort,
    ToolCallingRequest,
    ToolCallingResult,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
    EmbeddingResult,
)
from career_assistant.application.providers.egress import HostedEgressPolicy
from career_assistant.application.providers.fallback import (
    CompletingWithOptionalFallback,
    FallbackPolicy,
)
from career_assistant.application.providers.model_catalogue import (
    ModelCatalogue,
    load_model_catalogue,
)
from career_assistant.logconfig import log_event
from career_assistant.settings import ProviderSettings

_log = logging.getLogger(__name__)
_CATALOGUE_PATH = Path(__file__).resolve().parents[5] / "config" / "models.toml"


@dataclass(frozen=True, slots=True)
class _ProviderBuilders:
    completion: Callable[[ProviderConstruction], CompletionPort]
    embedding: Callable[[ProviderConstruction], EmbeddingPort]
    tool_calling: Callable[[ProviderConstruction], ToolCallingPort]
    hosted_permission: Callable[[HostedEgressPolicy], str] | None = None


_BUILDERS: dict[str, _ProviderBuilders] = {
    "hermetic": _ProviderBuilders(
        hermetic.completion, hermetic.embedding, hermetic.tool_calling
    ),
    "ollama": _ProviderBuilders(
        ollama.completion, ollama.embedding, ollama.tool_calling
    ),
    "openai": _ProviderBuilders(
        openai.completion,
        openai.embedding,
        openai.tool_calling,
        HostedEgressPolicy.assert_openai_constructible,
    ),
    "anthropic": _ProviderBuilders(
        anthropic.completion,
        anthropic.embedding,
        anthropic.tool_calling,
        HostedEgressPolicy.assert_anthropic_constructible,
    ),
}


def _builders(provider_id: str, kind: str) -> _ProviderBuilders:
    registered = _BUILDERS.get(provider_id)
    if registered is None:
        raise ProviderUnavailableError(f"unknown {kind} provider {provider_id!r}")
    return registered


@cache
def default_model_catalogue() -> ModelCatalogue:
    return load_model_catalogue(_CATALOGUE_PATH)


def build_egress_policy(settings: ProviderSettings) -> HostedEgressPolicy:
    return HostedEgressPolicy(
        allow_hosted=settings.allow_hosted_providers,
        openai_api_key=_secret_or_none(settings.openai_api_key),
        anthropic_api_key=_secret_or_none(settings.anthropic_api_key),
    )


def build_resilience(settings: ProviderSettings) -> ResiliencePolicy:
    return ResiliencePolicy(
        timeout_seconds=settings.provider_timeout_seconds,
        max_retries=settings.provider_max_retries,
        breaker=CircuitBreaker(settings.provider_breaker_failure_threshold),
    )


def build_completion_port(
    settings: ProviderSettings,
    *,
    transport: HttpTransport | None = None,
    egress: HostedEgressPolicy | None = None,
    provider_id: str | None = None,
    model_tag: str | None = None,
    catalogue: ModelCatalogue | None = None,
) -> CompletionPort:
    policy = egress or build_egress_policy(settings)
    http = transport or HttpxTransport()
    resilience = build_resilience(settings)
    selected = provider_id or settings.completion_provider
    primary = _completion_for(
        selected,
        settings=settings,
        egress=policy,
        transport=http,
        resilience=resilience,
        model_tag=model_tag,
        catalogue=catalogue or default_model_catalogue(),
    )
    if _builders(selected, "completion").hosted_permission is not None:
        wrapped = CompletingWithOptionalFallback(
            primary=primary,
            local=_BUILDERS["hermetic"].completion(
                ProviderConstruction(
                    settings,
                    policy,
                    http,
                    resilience,
                    None,
                    catalogue or default_model_catalogue(),
                )
            ),
            policy=FallbackPolicy(
                allow_local_fallback=settings.provider_allow_local_fallback
            ),
        )
        log_event(
            _log,
            "provider.constructed",
            kind="completion",
            provider_id=selected,
            fallback="hermetic",
            model_tag=model_tag or "",
        )
        return wrapped
    log_event(
        _log,
        "provider.constructed",
        kind="completion",
        provider_id=selected,
        model_tag=model_tag or "",
    )
    return primary


def build_embedding_port(
    settings: ProviderSettings,
    *,
    transport: HttpTransport | None = None,
    egress: HostedEgressPolicy | None = None,
    provider_id: str | None = None,
    model_tag: str | None = None,
    catalogue: ModelCatalogue | None = None,
) -> EmbeddingPort:
    policy = egress or build_egress_policy(settings)
    http = transport or HttpxTransport()
    resilience = build_resilience(settings)
    selected = provider_id or settings.embedding_provider
    port = _embedding_for(
        selected,
        settings=settings,
        egress=policy,
        transport=http,
        resilience=resilience,
        model_tag=model_tag,
        catalogue=catalogue or default_model_catalogue(),
    )
    log_event(_log, "provider.constructed", kind="embedding", provider_id=selected)
    return port


def _completion_for(
    provider_id: str,
    *,
    settings: ProviderSettings,
    egress: HostedEgressPolicy,
    transport: HttpTransport,
    resilience: ResiliencePolicy,
    model_tag: str | None,
    catalogue: ModelCatalogue,
) -> CompletionPort:
    builders = _builders(provider_id, "completion")
    port = builders.completion(
        ProviderConstruction(
            settings, egress, transport, resilience, model_tag, catalogue
        )
    )
    if builders.hosted_permission is not None:
        return _CallTimeEgressCompletion(port, settings=settings, hosted_kind=provider_id)
    return port


def _embedding_for(
    provider_id: str,
    *,
    settings: ProviderSettings,
    egress: HostedEgressPolicy,
    transport: HttpTransport,
    resilience: ResiliencePolicy,
    model_tag: str | None,
    catalogue: ModelCatalogue,
) -> EmbeddingPort:
    builders = _builders(provider_id, "embedding")
    port = builders.embedding(
        ProviderConstruction(
            settings, egress, transport, resilience, model_tag, catalogue
        )
    )
    if builders.hosted_permission is not None:
        return _CallTimeEgressEmbedding(port, settings=settings, hosted_kind=provider_id)
    return port


class _CallTimeEgressCompletion:
    """Re-assert hosted egress on every complete(), not only at construction."""

    def __init__(
        self,
        inner: CompletionPort,
        *,
        settings: ProviderSettings,
        hosted_kind: str,
    ) -> None:
        self._inner = inner
        self._settings = settings
        self._hosted_kind = hosted_kind

    @property
    def provider_id(self) -> str:
        return self._hosted_kind

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete(self, request: CompletionRequest) -> CompletionResult:
        _assert_hosted_call_permitted(self._settings, self._hosted_kind)
        return self._inner.complete(request)


class _CallTimeEgressEmbedding:
    """Re-assert hosted egress on every embed(), not only at construction."""

    def __init__(
        self,
        inner: EmbeddingPort,
        *,
        settings: ProviderSettings,
        hosted_kind: str,
    ) -> None:
        self._inner = inner
        self._settings = settings
        self._hosted_kind = hosted_kind

    @property
    def provider_id(self) -> str:
        return self._hosted_kind

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        _assert_hosted_call_permitted(self._settings, self._hosted_kind)
        return self._inner.embed(request)


def build_tool_calling_port(
    settings: ProviderSettings,
    *,
    transport: HttpTransport | None = None,
    egress: HostedEgressPolicy | None = None,
    provider_id: str | None = None,
    model_tag: str | None = None,
    catalogue: ModelCatalogue | None = None,
) -> ToolCallingPort:
    """The tool-calling adapter for the workspace's answer model."""
    policy = egress or build_egress_policy(settings)
    http = transport or HttpxTransport()
    resilience = build_resilience(settings)
    selected = provider_id or settings.completion_provider
    caller = _tool_caller_for(
        selected,
        settings=settings,
        egress=policy,
        transport=http,
        resilience=resilience,
        model_tag=model_tag,
        catalogue=catalogue or default_model_catalogue(),
    )
    if _builders(selected, "tool_calling").hosted_permission is not None:
        return _CallTimeEgressToolCaller(
            caller, settings=settings, hosted_kind=selected
        )
    log_event(
        _log,
        "provider.constructed",
        kind="tool_calling",
        provider_id=selected,
        model_tag=model_tag or "",
    )
    return caller


def _tool_caller_for(
    provider_id: str,
    *,
    settings: ProviderSettings,
    egress: HostedEgressPolicy,
    transport: HttpTransport,
    resilience: ResiliencePolicy,
    model_tag: str | None,
    catalogue: ModelCatalogue,
) -> ToolCallingPort:
    return _builders(provider_id, "tool_calling").tool_calling(
        ProviderConstruction(
            settings, egress, transport, resilience, model_tag, catalogue
        )
    )


class _CallTimeEgressToolCaller:
    """Re-assert hosted egress on every tool-calling turn, not only at construction."""

    def __init__(
        self,
        inner: ToolCallingPort,
        *,
        settings: ProviderSettings,
        hosted_kind: str,
    ) -> None:
        self._inner = inner
        self._settings = settings
        self._hosted_kind = hosted_kind

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete(self, request: ToolCallingRequest) -> ToolCallingResult:
        _assert_hosted_call_permitted(self._settings, self._hosted_kind)
        return self._inner.complete(request)


def _assert_hosted_call_permitted(settings: ProviderSettings, hosted_kind: str) -> None:
    policy = build_egress_policy(settings)
    permit = _builders(hosted_kind, "completion").hosted_permission
    if permit is not None:
        permit(policy)


def _secret_or_none(value: object) -> str | None:
    if value is None:
        return None
    raw = value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)
    return raw or None
