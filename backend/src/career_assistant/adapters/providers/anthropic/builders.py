"""Anthropic construction: large model budgets with independent embeddings."""

from __future__ import annotations

from career_assistant.adapters.providers.anthropic.completion import (
    AnthropicCompletionAdapter,
)
from career_assistant.adapters.providers.construction import ProviderConstruction
from career_assistant.adapters.providers.tool_calling import AnthropicToolCaller
from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.errors import ProviderUnavailableError
from career_assistant.application.ports.tool_calling import ToolCallingPort


def completion(context: ProviderConstruction) -> CompletionPort:
    key = context.egress.assert_anthropic_constructible()
    tag = context.model_tag or context.settings.anthropic_completion_model
    return AnthropicCompletionAdapter(
        api_key=key,
        model_tag=tag,
        transport=context.transport,
        resilience=context.resilience,
        profile=context.catalogue.profile("anthropic", tag),
        gate=context.hosted_gate(),
    )


def embedding(context: ProviderConstruction) -> EmbeddingPort:
    del context
    raise ProviderUnavailableError(
        "anthropic does not provide embeddings; configure an independent "
        "embedding provider"
    )


def tool_calling(context: ProviderConstruction) -> ToolCallingPort:
    key = context.egress.assert_anthropic_constructible()
    tag = context.model_tag or context.settings.anthropic_completion_model
    return AnthropicToolCaller(
        api_key=key,
        model_tag=tag,
        transport=context.transport,
        resilience=context.resilience,
        profile=context.catalogue.profile("anthropic", tag),
        gate=context.hosted_gate(),
    )
