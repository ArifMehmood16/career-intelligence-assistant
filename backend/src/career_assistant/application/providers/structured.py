"""Structured completion over any completion port (PLAN 18.2).

The contract's Pydantic model supplies the schema, parses the reply and, when the
reply is invalid, the text of one repair request. A reply that is still invalid,
or one cut by the output limit, raises a typed error: the caller records an
incomplete analysis rather than using part of an answer.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from career_assistant.application.contracts.repair import (
    render_repair_message,
    summarize_validation_error,
)
from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.errors import (
    StructuredOutputInvalidError,
    StructuredOutputTruncatedError,
)
from career_assistant.application.ports.progress import plan_calls
from career_assistant.application.ports.structured import (
    StructuredRequest,
    StructuredResult,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)
from career_assistant.application.providers.logging_ports import llm_operation
from career_assistant.logconfig import log_event

_log = logging.getLogger(__name__)
_TRUNCATED = "length"


@dataclass(frozen=True, slots=True)
class _Attempt:
    result: CompletionResult
    user: str


class StructuredCompleter:
    """Implements StructuredCompletionPort on top of a CompletionPort."""

    def __init__(self, completion: CompletionPort) -> None:
        self._completion = completion

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return self._completion.capabilities

    def complete_structured[T: BaseModel](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]:
        schema = request.contract.model_json_schema()
        first = self._attempt(request, request.user, schema, number=1)
        try:
            value = request.contract.model_validate_json(first.result.text)
        except ValidationError as error:
            _log_invalid(request, attempt=1, error=error)
            repair_user = _repair_user(request.user, first.result.text, error)
        else:
            _log_parsed(request, attempt=1, value=value)
            return _result(value, [first])
        plan_calls(model=1)
        second = self._attempt(request, repair_user, schema, number=2)
        try:
            value = request.contract.model_validate_json(second.result.text)
        except ValidationError as error:
            log_event(
                _log,
                "Model reply still did not match its contract after the repair",
                contract=_version(request),
                attempt=2,
                errors=error.error_count(),
                problems=summarize_validation_error(error),
            )
            raise StructuredOutputInvalidError(
                f"{_version(request)} reply invalid after one repair",
                contract_version=_version(request),
                error_count=error.error_count(),
            ) from error
        _log_parsed(request, attempt=2, value=value)
        return _result(value, [first, second])

    def _attempt[T: BaseModel](
        self,
        request: StructuredRequest[T],
        user: str,
        schema: dict[str, Any],
        *,
        number: int,
    ) -> _Attempt:
        native = self._completion.capabilities.supports_structured_output
        system = request.system if native else _with_schema(request.system, schema)
        with llm_operation(_version(request), attempt=number):
            result = self._completion.complete(
                CompletionRequest(
                    system=system,
                    user=user,
                    max_output_tokens=request.max_output_tokens,
                    json_schema=schema if native else None,
                    temperature=request.temperature,
                    seed=request.seed,
                )
            )
        if result.finish_reason == _TRUNCATED:
            log_event(
                _log,
                "Model reply cut off by the output limit",
                contract=_version(request),
                attempt=number,
            )
            raise StructuredOutputTruncatedError(
                f"{_version(request)} reply cut by the output limit",
                contract_version=_version(request),
                output_tokens=result.output_tokens,
            )
        return _Attempt(result=result, user=user)


def _log_invalid[T: BaseModel](
    request: StructuredRequest[T], *, attempt: int, error: ValidationError
) -> None:
    log_event(
        _log,
        "Model reply did not match its contract, asking for a repair",
        contract=_version(request),
        attempt=attempt,
        errors=error.error_count(),
        problems=summarize_validation_error(error),
    )


def _log_parsed[T: BaseModel](
    request: StructuredRequest[T], *, attempt: int, value: T
) -> None:
    describe = getattr(value, "log_summary", None)
    summary = describe() if callable(describe) else type(value).__name__
    log_event(
        _log,
        f"Model reply parsed: {summary}",
        contract=_version(request),
        attempt=attempt,
    )


def _result[T: BaseModel](value: T, attempts: list[_Attempt]) -> StructuredResult[T]:
    last = attempts[-1].result
    return StructuredResult(
        value=value,
        provider_id=last.provider_id,
        model_tag=last.model_tag,
        left_machine=any(a.result.left_machine for a in attempts),
        attempts=len(attempts),
        input_tokens=_total(a.result.input_tokens for a in attempts),
        output_tokens=_total(a.result.output_tokens for a in attempts),
    )


def _repair_user(user: str, previous: str, error: ValidationError) -> str:
    # The previous reply is model output about untrusted text: delimited, not obeyed.
    return (
        f"{user}\n\n<previous_response>\n{previous}\n</previous_response>\n\n"
        f"{render_repair_message(error)}"
    )


def _with_schema(system: str, schema: dict[str, Any]) -> str:
    instruction = "Respond with JSON only matching this schema:"
    return f"{system}\n\n{instruction}\n{json.dumps(schema)}"


def _version[T: BaseModel](request: StructuredRequest[T]) -> str:
    return str(getattr(request.contract, "contract_version", request.contract.__name__))


def _total(values: Any) -> int | None:
    known = [v for v in values if v is not None]
    return sum(known) if known else None
