"""Hermetic structured completion: a registry of rule-based fixtures (PLAN 18.4).

A test fixture only. Each contract gets its builder from the task that first uses
it; a contract with no builder is refused rather than answered with a guess.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel

from career_assistant.adapters.providers.hermetic.chunking_rules import (
    cv_chunks,
    job_chunks,
    letter_chunks,
)
from career_assistant.adapters.providers.hermetic.judging_rules import judge_verdicts
from career_assistant.application.contracts.chunking import (
    CoverLetterChunkResponse,
    CvChunkResponse,
    JobChunkResponse,
)
from career_assistant.application.contracts.judge import JudgeResponse
from career_assistant.application.ports.errors import ProviderUnavailableError
from career_assistant.application.ports.structured import (
    StructuredRequest,
    StructuredResult,
)
from career_assistant.application.ports.types import CapabilityDescriptor

Builder = Callable[[str], dict[str, Any]]
DEFAULT_BUILDERS: Mapping[type[BaseModel], Builder] = {
    CvChunkResponse: cv_chunks,
    CoverLetterChunkResponse: letter_chunks,
    JobChunkResponse: job_chunks,
    JudgeResponse: judge_verdicts,
}


class HermeticStructuredCompleter:
    provider_id = "hermetic"
    model_tag = "rules-v1"

    def __init__(
        self, builders: Mapping[type[BaseModel], Builder] | None = None
    ) -> None:
        self._builders = DEFAULT_BUILDERS if builders is None else builders

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id=self.provider_id,
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=32_768,
            max_output_tokens=8_192,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete_structured[T: BaseModel](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]:
        builder = self._builders.get(request.contract)
        if builder is None:
            raise ProviderUnavailableError(
                f"no hermetic fixture for {request.contract.__name__}"
            )
        value = request.contract.model_validate(builder(request.user))
        return StructuredResult(
            value=value,
            provider_id=self.provider_id,
            model_tag=self.model_tag,
            left_machine=False,
            attempts=1,
            input_tokens=None,
            output_tokens=None,
        )
