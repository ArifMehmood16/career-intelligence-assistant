"""Local provider construction, including model identity and memory limits."""

from __future__ import annotations

from functools import partial

from career_assistant.adapters.providers.construction import ProviderConstruction
from career_assistant.adapters.providers.ollama.completion import (
    OllamaCompletionAdapter,
)
from career_assistant.adapters.providers.ollama.digest import ollama_model_digest
from career_assistant.adapters.providers.ollama.embedding import OllamaEmbeddingAdapter
from career_assistant.adapters.providers.tool_calling import OllamaToolCaller
from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.tool_calling import ToolCallingPort


def completion(context: ProviderConstruction) -> CompletionPort:
    tag = context.model_tag or context.settings.ollama_completion_model or "qwen2.5:7b"
    return OllamaCompletionAdapter(
        base_url=context.settings.ollama_base_url,
        model_tag=tag,
        transport=context.transport,
        resilience=context.resilience,
        profile=context.catalogue.profile("ollama", tag),
        digest_lookup=partial(
            ollama_model_digest,
            context.transport,
            base_url=context.settings.ollama_base_url,
            model_tag=tag,
            timeout_seconds=context.resilience.timeout_seconds,
        ),
    )


def embedding(context: ProviderConstruction) -> EmbeddingPort:
    tag = (
        context.model_tag
        or context.settings.ollama_embedding_model
        or "nomic-embed-text"
    )
    return OllamaEmbeddingAdapter(
        base_url=context.settings.ollama_base_url,
        model_tag=tag,
        transport=context.transport,
        resilience=context.resilience,
        profile=context.catalogue.profile("ollama", tag),
    )


def tool_calling(context: ProviderConstruction) -> ToolCallingPort:
    tag = context.model_tag or context.settings.ollama_completion_model or "qwen2.5:7b"
    return OllamaToolCaller(
        base_url=context.settings.ollama_base_url,
        model_tag=tag,
        transport=context.transport,
        resilience=context.resilience,
        profile=context.catalogue.profile("ollama", tag),
    )
