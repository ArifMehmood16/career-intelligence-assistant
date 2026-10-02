"""Offline fixtures remain explicitly selected by tests."""

from __future__ import annotations

from career_assistant.adapters.providers.construction import ProviderConstruction
from career_assistant.adapters.providers.hermetic.completion import (
    HermeticCompletionAdapter,
)
from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.embedding import EmbeddingPort
from career_assistant.application.ports.tool_calling import (
    HermeticToolCaller,
    ToolCallingPort,
)


def completion(context: ProviderConstruction) -> CompletionPort:
    del context
    return HermeticCompletionAdapter()


def embedding(context: ProviderConstruction) -> EmbeddingPort:
    del context
    return HermeticEmbeddingAdapter()


def tool_calling(context: ProviderConstruction) -> ToolCallingPort:
    del context
    return HermeticToolCaller()
