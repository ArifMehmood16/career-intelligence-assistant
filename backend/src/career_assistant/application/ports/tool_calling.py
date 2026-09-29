"""Tool calling: messages and tool schemas in, tool calls or a final message out.

A narrow port beside completion and structured completion (ADR 015). Adapters
translate this shape into one vendor's tool-calling API. The application never
sees that shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from career_assistant.application.ports.types import CapabilityDescriptor


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Literal["user", "assistant", "tool"]
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    call_id: str = ""
    name: str = ""


@dataclass(frozen=True, slots=True)
class ToolCallingRequest:
    system: str
    messages: tuple[ChatMessage, ...]
    tools: tuple[ToolDefinition, ...]
    max_output_tokens: int


@dataclass(frozen=True, slots=True)
class ToolCallingResult:
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    provider_id: str = ""
    model_tag: str = ""
    left_machine: bool = False
    input_tokens: int | None = None
    output_tokens: int | None = None


class ToolCallingPort(Protocol):
    @property
    def capabilities(self) -> CapabilityDescriptor: ...

    def complete(self, request: ToolCallingRequest) -> ToolCallingResult: ...


@dataclass
class HermeticToolCaller:
    """Plays back a scripted sequence. Drives the agent loop with no model."""

    script: list[ToolCallingResult] = field(default_factory=list)
    requests: list[ToolCallingRequest] = field(default_factory=list)

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="hermetic",
            supports_completion=False,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=8_192,
            max_output_tokens=1_024,
            embedding_dimensions=None,
            leaves_machine=False,
            supports_tool_calling=True,
        )

    def complete(self, request: ToolCallingRequest) -> ToolCallingResult:
        self.requests.append(request)
        if not self.script:
            return ToolCallingResult(
                content="",
                provider_id="hermetic",
                model_tag="rules-v1",
                left_machine=False,
            )
        return self.script.pop(0)
