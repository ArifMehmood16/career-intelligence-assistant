"""A completion port that plays back scripted replies and records every request."""

from __future__ import annotations

from dataclasses import dataclass, field

from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)


@dataclass(frozen=True)
class Reply:
    text: str
    finish_reason: str | None = "stop"
    input_tokens: int | None = 10
    output_tokens: int | None = 5


@dataclass
class ScriptedCompletion:
    replies: list[Reply]
    structured_output: bool = True
    requests: list[CompletionRequest] = field(default_factory=list)

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="scripted",
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=self.structured_output,
            context_window_tokens=32_768,
            max_output_tokens=8_192,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self.requests.append(request)
        reply = self.replies[len(self.requests) - 1]
        return CompletionResult(
            text=reply.text,
            provider_id="scripted",
            model_tag="scripted-v1",
            left_machine=False,
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
            finish_reason=reply.finish_reason,
        )
