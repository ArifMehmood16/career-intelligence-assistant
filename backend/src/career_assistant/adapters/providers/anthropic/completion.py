"""Anthropic messages adapter — completion only; no embeddings."""

from __future__ import annotations

import json
from typing import Any

from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.providers.resilience import (
    ResiliencePolicy,
    classify_http_status,
)
from career_assistant.application.ports.errors import (
    ProviderInputTooLargeError,
    ProviderRefusedError,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)

_MAX_INPUT_CHARS = 200_000


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
    ) -> None:
        self._api_key = api_key
        self._model_tag = model_tag
        self._transport = transport
        self._resilience = resilience
        self._base_url = base_url.rstrip("/")

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id=self.provider_id,
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=200_000,
            max_output_tokens=4_096,
            embedding_dimensions=None,
            leaves_machine=True,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        if len(request.system) + len(request.user) > _MAX_INPUT_CHARS:
            raise ProviderInputTooLargeError("anthropic input too large")

        user_content = request.user
        if request.json_schema is not None:
            user_content = (
                f"{request.user}\n\nRespond with JSON only matching this schema:\n"
                f"{json.dumps(request.json_schema)}"
            )

        def _call() -> CompletionResult:
            response = self._transport.request(
                "POST",
                f"{self._base_url}/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json_body={
                    "model": self._model_tag,
                    "max_tokens": request.max_output_tokens,
                    "system": request.system,
                    "messages": [{"role": "user", "content": user_content}],
                },
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
            )

        return self._resilience.run(_call)


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None
