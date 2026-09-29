"""Shared provider result types — no vendor shapes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class CapabilityDescriptor:
    """What a provider can do. Application reads this; never branches on name."""

    provider_id: str
    supports_completion: bool
    supports_embedding: bool
    supports_structured_output: bool
    context_window_tokens: int
    max_output_tokens: int
    embedding_dimensions: int | None
    leaves_machine: bool
    supports_tool_calling: bool = False
    supports_prompt_caching: bool = False
    supports_temperature: bool = False
    supports_seed: bool = False


@dataclass(frozen=True, slots=True)
class ModelProfile:
    """Published limits and capabilities of one model tag, from configuration."""

    context_window_tokens: int
    max_output_tokens: int
    supports_tool_calling: bool = False
    supports_prompt_caching: bool = False
    supports_temperature: bool = False
    supports_seed: bool = False
    # The API enforces a JSON schema itself; otherwise the adapter asks in the prompt.
    native_structured_output: bool = False
    embedding_query_prefix: str = ""
    embedding_document_prefix: str = ""


@dataclass(frozen=True, slots=True)
class CompletionRequest:
    """Use-case shaped completion input. No chat-message or tool arrays."""

    system: str
    user: str
    max_output_tokens: int
    json_schema: dict[str, Any] | None = None
    # Sent only when the model's capability descriptor says it accepts them.
    temperature: float | None = None
    seed: int | None = None


@dataclass(frozen=True, slots=True)
class CompletionResult:
    text: str
    provider_id: str
    model_tag: str
    left_machine: bool
    input_tokens: int | None = None
    output_tokens: int | None = None
    fallback_used: bool = False
    latency_ms: int | None = None
    finish_reason: str | None = None


EmbeddingInputType = Literal["query", "document"]


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    texts: tuple[str, ...]
    max_chars_per_text: int
    # None is a v1 request: embedded exactly as before, with no task prefix.
    input_type: EmbeddingInputType | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vectors: tuple[tuple[float, ...], ...]
    provider_id: str
    model_tag: str
    dimensions: int
    left_machine: bool
    input_tokens: int | None = None
    latency_ms: int | None = None


@dataclass(frozen=True, slots=True)
class CallRecord:
    """Identifiers and counts only — never content."""

    provider_id: str
    model_tag: str
    operation: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    estimated_cost_usd: float | None
    left_machine: bool
    fallback_used: bool = False
    metadata: dict[str, str] = field(default_factory=dict)
