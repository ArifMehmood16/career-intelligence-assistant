"""OpenAI construction: gated credentials, model capabilities and shared limits."""

from __future__ import annotations

from career_assistant.adapters.providers.construction import ProviderConstruction
from career_assistant.adapters.providers.openai.completion import (
    OpenAICompletionAdapter,
)
from career_assistant.adapters.providers.openai.embedding import OpenAIEmbeddingAdapter
from career_assistant.adapters.providers.tool_calling import OpenAIToolCaller
from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.tool_calling import ToolCallingPort


def completion(context: ProviderConstruction) -> CompletionPort:
    key = context.egress.assert_openai_constructible()
    tag = context.model_tag or context.settings.openai_completion_model
    return OpenAICompletionAdapter(
        api_key=key,
        model_tag=tag,
        transport=context.transport,
        resilience=context.resilience,
        profile=context.catalogue.profile("openai", tag),
        gate=context.hosted_gate(),
    )


def embedding(context: ProviderConstruction) -> EmbeddingPort:
    key = context.egress.assert_openai_constructible()
    tag = context.model_tag or context.settings.openai_embedding_model
    return OpenAIEmbeddingAdapter(
        api_key=key,
        model_tag=tag,
        transport=context.transport,
        resilience=context.resilience,
        profile=context.catalogue.profile("openai", tag),
        gate=context.hosted_gate(),
    )


def tool_calling(context: ProviderConstruction) -> ToolCallingPort:
    key = context.egress.assert_openai_constructible()
    tag = context.model_tag or context.settings.openai_completion_model
    return OpenAIToolCaller(
        api_key=key,
        model_tag=tag,
        transport=context.transport,
        resilience=context.resilience,
        profile=context.catalogue.profile("openai", tag),
        gate=context.hosted_gate(),
    )
