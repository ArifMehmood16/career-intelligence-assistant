"""Fallback policy — never silent when a hosted call degrades to local."""

from __future__ import annotations

from dataclasses import dataclass

from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.errors import ProviderError
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)


@dataclass(frozen=True, slots=True)
class FallbackPolicy:
    allow_local_fallback: bool


class CompletingWithOptionalFallback:
    """Wraps a primary completer; local fallback only when policy allows and says so."""

    def __init__(
        self,
        primary: CompletionPort,
        local: CompletionPort,
        policy: FallbackPolicy,
    ) -> None:
        self._primary = primary
        self._local = local
        self._policy = policy

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._primary.capabilities

    def complete(self, request: CompletionRequest) -> CompletionResult:
        try:
            return self._primary.complete(request)
        except ProviderError:
            if not self._policy.allow_local_fallback:
                raise
            result = self._local.complete(request)
            return CompletionResult(
                text=result.text,
                provider_id=result.provider_id,
                model_tag=result.model_tag,
                left_machine=result.left_machine,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                fallback_used=True,
                latency_ms=result.latency_ms,
            )
