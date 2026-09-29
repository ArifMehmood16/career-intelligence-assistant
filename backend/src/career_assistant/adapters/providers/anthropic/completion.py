"""Anthropic messages adapter — completion only; no embeddings."""

from __future__ import annotations

import json
from typing import Any

from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.providers.resilience import (
    ResiliencePolicy,
    classify_http_status,
)
from career_assistant.adapters.providers.schema_dialects import (
    anthropic_output_schema,
)
from career_assistant.application.ports.errors import (
    ProviderInputTooLargeError,
    ProviderRefusedError,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
    ModelProfile,
)

_MAX_INPUT_CHARS = 200_000


# The v1 constants, used when no catalogue profile is passed (tests, old callers).
_DEFAULT_PROFILE = ModelProfile(context_window_tokens=200_000, max_output_tokens=4_096)


class AnthropicCompletionAdapter:
    provider_id = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        model_tag: str,
        transport: HttpTransport,
        resilience: ResiliencePolicy,
        base_url: str = "https://api.anthropic.com/v1",
        profile: ModelProfile | None = None,
    ) -> None:
        self._api_key = api_key
        self._model_tag = model_tag
        self._transport = transport
        self._resilience = resilience
        self._profile = profile or _DEFAULT_PROFILE
        self._base_url = base_url.rstrip("/")

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id=self.provider_id,
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=self._profile.context_window_tokens,
            max_output_tokens=self._profile.max_output_tokens,
            embedding_dimensions=None,
            leaves_machine=True,
            supports_tool_calling=self._profile.supports_tool_calling,
            supports_prompt_caching=self._profile.supports_prompt_caching,
            supports_temperature=self._profile.supports_temperature,
            supports_seed=self._profile.supports_seed,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        if len(request.system) + len(request.user) > _MAX_INPUT_CHARS:
            raise ProviderInputTooLargeError("anthropic input too large")

        body = self._body(request)

        def _call() -> CompletionResult:
            response = self._transport.request(
                "POST",
                f"{self._base_url}/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json_body=body,
                timeout_seconds=self._resilience.timeout_seconds,
            )
            classify_http_status(response.status_code)
            data = json.loads(response.body.decode("utf-8"))
            if data.get("stop_reason") == "refusal":
                raise ProviderRefusedError("anthropic refused the request")
            blocks = data.get("content") or []
            text_parts = [
                str(block.get("text", ""))
                for block in blocks
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            text = "".join(text_parts)
            usage = data.get("usage") or {}
            return CompletionResult(
                text=text,
                provider_id=self.provider_id,
                model_tag=self._model_tag,
                left_machine=True,
                input_tokens=_int_or_none(usage.get("input_tokens")),
                output_tokens=_int_or_none(usage.get("output_tokens")),
                finish_reason=_finish_reason(data.get("stop_reason")),
            )

        return self._resilience.run(_call)

    def _body(self, request: CompletionRequest) -> dict[str, object]:
        body: dict[str, object] = {
            "model": self._model_tag,
            "max_tokens": request.max_output_tokens,
            "system": request.system,
            "messages": [{"role": "user", "content": request.user}],
        }
        schema = request.json_schema
        if schema is not None and self._profile.native_structured_output:
            body["output_config"] = {
                "format": {
                    "type": "json_schema",
                    "schema": anthropic_output_schema(schema),
                }
            }
        elif schema is not None:
            # Models without structured outputs are asked in the prompt, as in v1.
            body["messages"] = [
                {
                    "role": "user",
                    "content": f"{request.user}\n\nRespond with JSON only matching "
                    f"this schema:\n{json.dumps(schema)}",
                }
            ]
        if request.temperature is not None and self._profile.supports_temperature:
            body["temperature"] = request.temperature
        return body


# Anthropic's stop reasons, in the vocabulary callers already check.
_FINISH_REASONS = {"end_turn": "stop", "stop_sequence": "stop", "max_tokens": "length"}


def _finish_reason(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return _FINISH_REASONS.get(value, value)


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None
