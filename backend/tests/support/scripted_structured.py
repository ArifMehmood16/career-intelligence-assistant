"""A structured completion port that plays back contract objects or errors."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from career_assistant.application.ports.structured import (
    StructuredRequest,
    StructuredResult,
)
from career_assistant.application.ports.types import CapabilityDescriptor


@dataclass
class ScriptedStructured:
    replies: list[BaseModel | Exception]
    context_window_tokens: int = 32_768
    max_output_tokens: int = 8_192
    requests: list[StructuredRequest[BaseModel]] = field(default_factory=list)
    supports_temperature: bool = False
    supports_seed: bool = False
    model_tag: str = "scripted-v1"
    model_digest: str | None = None

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="scripted",
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=self.context_window_tokens,
            max_output_tokens=self.max_output_tokens,
            embedding_dimensions=None,
            leaves_machine=False,
            supports_temperature=self.supports_temperature,
            supports_seed=self.supports_seed,
            model_digest=self.model_digest,
        )

    def complete_structured[T: BaseModel](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]:
        self.requests.append(request)  # type: ignore[arg-type]
        reply = self.replies[len(self.requests) - 1]
        if isinstance(reply, Exception):
            raise reply
        assert isinstance(reply, request.contract), (
            "scripted reply is the wrong contract"
        )
        return StructuredResult(
            value=reply,
            provider_id="scripted",
            model_tag=self.model_tag,
            left_machine=False,
            attempts=1,
            input_tokens=100,
            output_tokens=50,
        )
