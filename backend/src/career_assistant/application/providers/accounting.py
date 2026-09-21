"""Call accounting — identifiers and counts only, never content."""

from __future__ import annotations

from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.types import (
    CallRecord,
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)


class CallAccountant:
    def __init__(self) -> None:
        self._records: list[CallRecord] = []

    def record(self, entry: CallRecord) -> None:
        self._records.append(entry)

    @property
    def records(self) -> tuple[CallRecord, ...]:
        return tuple(self._records)


class AccountingCompletion:
    """Records provider/model/token counts after each complete(), never the text."""

    def __init__(
        self,
        inner: CompletionPort,
        accountant: CallAccountant,
        *,
        workspace_id: str,
        purpose: str,
    ) -> None:
        self._inner = inner
        self._accountant = accountant
        self._workspace_id = workspace_id
        self._purpose = purpose

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._inner.capabilities

    def complete(self, request: CompletionRequest) -> CompletionResult:
        result = self._inner.complete(request)
        self._accountant.record(
            CallRecord(
                provider_id=result.provider_id,
                model_tag=result.model_tag,
                operation="complete",
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                latency_ms=result.latency_ms,
                estimated_cost_usd=None,
                left_machine=result.left_machine,
                fallback_used=result.fallback_used,
                metadata={
                    "workspace_id": self._workspace_id,
                    "purpose": self._purpose,
                },
            )
        )
        return result
