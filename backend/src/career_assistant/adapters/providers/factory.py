"""Composition root for completion and embedding adapters."""

from __future__ import annotations

import logging

from career_assistant.adapters.providers.anthropic.completion import (
    AnthropicCompletionAdapter,
)
from career_assistant.adapters.providers.hermetic.completion import (
    HermeticCompletionAdapter,
)
from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.providers.httpx_transport import HttpxTransport
from career_assistant.adapters.providers.ollama.completion import (
    OllamaCompletionAdapter,
)
from career_assistant.adapters.providers.ollama.embedding import OllamaEmbeddingAdapter
from career_assistant.adapters.providers.openai.completion import (
    OpenAICompletionAdapter,
)
from career_assistant.adapters.providers.openai.embedding import OpenAIEmbeddingAdapter
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
)
from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.errors import ProviderUnavailableError
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
from career_assistant.logconfig import log_event
from career_assistant.settings import ProviderSettings

_log = logging.getLogger(__name__)


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
) -> CompletionPort:
    policy = egress or build_egress_policy(settings)
    http = transport or HttpxTransport()
    resilience = build_resilience(settings)
    hermetic = HermeticCompletionAdapter()
    selected = provider_id or settings.completion_provider
    primary = _completion_for(
        selected,
        settings=settings,
        egress=policy,
        transport=http,
        resilience=resilience,
        model_tag=model_tag,
    )
    if selected in {"openai", "anthropic"}:
        wrapped = CompletingWithOptionalFallback(
            primary=primary,
            local=hermetic,
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
    model_tag: str | None = None,
) -> CompletionPort:
    if provider_id == "hermetic":
        return HermeticCompletionAdapter()
    if provider_id == "ollama":
        return OllamaCompletionAdapter(
            base_url=settings.ollama_base_url,
            model_tag=model_tag or settings.ollama_completion_model or "llama3.2",
            transport=transport,
            resilience=resilience,
        )
    if provider_id == "openai":
        key = egress.assert_openai_constructible()
        return _CallTimeEgressCompletion(
            OpenAICompletionAdapter(
                api_key=key,
                model_tag=model_tag or settings.openai_completion_model,
                transport=transport,
                resilience=resilience,
            ),
            settings=settings,
            hosted_kind="openai",
        )
    if provider_id == "anthropic":
        key = egress.assert_anthropic_constructible()
        return _CallTimeEgressCompletion(
            AnthropicCompletionAdapter(
                api_key=key,
                model_tag=model_tag or settings.anthropic_completion_model,
                transport=transport,
                resilience=resilience,
            ),
            settings=settings,
            hosted_kind="anthropic",
        )
    raise ProviderUnavailableError(f"unknown completion provider {provider_id!r}")


def _embedding_for(
    provider_id: str,
    *,
    settings: ProviderSettings,
    egress: HostedEgressPolicy,
    transport: HttpTransport,
    resilience: ResiliencePolicy,
    model_tag: str | None = None,
) -> EmbeddingPort:
    if provider_id == "hermetic":
        return HermeticEmbeddingAdapter()
    if provider_id == "ollama":
        return OllamaEmbeddingAdapter(
            base_url=settings.ollama_base_url,
            model_tag=(
                model_tag or settings.ollama_embedding_model or "nomic-embed-text"
            ),
            transport=transport,
            resilience=resilience,
        )
    if provider_id == "openai":
        key = egress.assert_openai_constructible()
        return _CallTimeEgressEmbedding(
            OpenAIEmbeddingAdapter(
                api_key=key,
                model_tag=model_tag or settings.openai_embedding_model,
                transport=transport,
                resilience=resilience,
            ),
            settings=settings,
            hosted_kind="openai",
        )
    if provider_id == "anthropic":
        raise ProviderUnavailableError(
            "anthropic does not provide embeddings; configure an independent "
            "embedding provider"
        )
    raise ProviderUnavailableError(f"unknown embedding provider {provider_id!r}")


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


def _assert_hosted_call_permitted(settings: ProviderSettings, hosted_kind: str) -> None:
    policy = build_egress_policy(settings)
    if hosted_kind == "openai":
        policy.assert_openai_constructible()
        return
    policy.assert_anthropic_constructible()


def _secret_or_none(value: object) -> str | None:
    if value is None:
        return None
    raw = value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)
    return raw or None
