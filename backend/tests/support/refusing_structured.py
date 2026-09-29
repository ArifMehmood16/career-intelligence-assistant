"""Hermetic structured completion that fails one contract, for v2 failure paths."""

from __future__ import annotations

from pydantic import BaseModel

from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.application.contracts.chunking import CvChunkingResponse
from career_assistant.application.contracts.judge import JudgeResponse
from career_assistant.application.ports.errors import (
    ProviderRefusedError,
    StructuredOutputInvalidError,
)
from career_assistant.application.ports.structured import (
    StructuredRequest,
    StructuredResult,
)
from career_assistant.application.ports.types import CapabilityDescriptor


class RefusingJudge:
    """Chunks and relates terms hermetically; refuses every judge call."""

    def __init__(self) -> None:
        self._inner = HermeticStructuredCompleter()

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete_structured[T: BaseModel](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]:
        if request.contract is JudgeResponse:
            raise ProviderRefusedError("refused")
        return self._inner.complete_structured(request)


class InvalidCvChunker:
    """Every CV chunk plan stays invalid after its repair call."""

    def __init__(self) -> None:
        self._inner = HermeticStructuredCompleter()

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete_structured[T: BaseModel](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]:
        if request.contract is CvChunkingResponse:
            raise StructuredOutputInvalidError(
                "invalid", contract_version="scripted", error_count=1
            )
        return self._inner.complete_structured(request)
