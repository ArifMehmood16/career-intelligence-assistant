"""Composition root for completion and embedding adapters."""

from __future__ import annotations

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
from career_assistant.application.providers.egress import HostedEgressPolicy
from career_assistant.application.providers.fallback import (
    CompletingWithOptionalFallback,
    FallbackPolicy,
)
from career_assistant.settings import ProviderSettings


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
) -> CompletionPort:
    policy = egress or build_egress_policy(settings)
    http = transport or HttpxTransport()
    resilience = build_resilience(settings)
    hermetic = HermeticCompletionAdapter()
    primary = _completion_for(
        settings.completion_provider,
        settings=settings,
        egress=policy,
        transport=http,
        resilience=resilience,
    )
    if settings.completion_provider in {"openai", "anthropic"}:
        return CompletingWithOptionalFallback(
            primary=primary,
            local=hermetic,
            policy=FallbackPolicy(
                allow_local_fallback=settings.provider_allow_local_fallback
            ),
        )
    return primary


def build_embedding_port(
    settings: ProviderSettings,
    *,
    transport: HttpTransport | None = None,
    egress: HostedEgressPolicy | None = None,
) -> EmbeddingPort:
    policy = egress or build_egress_policy(settings)
    http = transport or HttpxTransport()
    resilience = build_resilience(settings)
    return _embedding_for(
        settings.embedding_provider,
        settings=settings,
        egress=policy,
        transport=http,
        resilience=resilience,
    )


def _completion_for(
    provider_id: str,
    *,
    settings: ProviderSettings,
    egress: HostedEgressPolicy,
    transport: HttpTransport,
    resilience: ResiliencePolicy,
) -> CompletionPort:
    if provider_id == "hermetic":
        return HermeticCompletionAdapter()
    if provider_id == "ollama":
        return OllamaCompletionAdapter(
            base_url=settings.ollama_base_url,
            model_tag=settings.ollama_completion_model or "llama3.2",
            transport=transport,
            resilience=resilience,
        )
    if provider_id == "openai":
        key = egress.assert_openai_constructible()
        return OpenAICompletionAdapter(
            api_key=key,
            model_tag=settings.openai_completion_model,
            transport=transport,
            resilience=resilience,
        )
    if provider_id == "anthropic":
        key = egress.assert_anthropic_constructible()
        return AnthropicCompletionAdapter(
            api_key=key,
            model_tag=settings.anthropic_completion_model,
            transport=transport,
            resilience=resilience,
        )
    raise ProviderUnavailableError(f"unknown completion provider {provider_id!r}")


def _embedding_for(
    provider_id: str,
    *,
    settings: ProviderSettings,
    egress: HostedEgressPolicy,
    transport: HttpTransport,
    resilience: ResiliencePolicy,
) -> EmbeddingPort:
    if provider_id == "hermetic":
        return HermeticEmbeddingAdapter()
    if provider_id == "ollama":
        return OllamaEmbeddingAdapter(
            base_url=settings.ollama_base_url,
            model_tag=settings.ollama_embedding_model or "nomic-embed-text",
            transport=transport,
            resilience=resilience,
        )
    if provider_id == "openai":
        key = egress.assert_openai_constructible()
        return OpenAIEmbeddingAdapter(
            api_key=key,
            model_tag=settings.openai_embedding_model,
            transport=transport,
            resilience=resilience,
        )
    if provider_id == "anthropic":
        raise ProviderUnavailableError(
            "anthropic does not provide embeddings; configure an independent "
            "embedding provider"
        )
    raise ProviderUnavailableError(f"unknown embedding provider {provider_id!r}")


def _secret_or_none(value: object) -> str | None:
    if value is None:
        return None
    raw = value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)
    return raw or None
