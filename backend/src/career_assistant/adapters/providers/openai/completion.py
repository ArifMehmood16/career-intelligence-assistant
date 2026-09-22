"""OpenAI chat completions adapter — hosted; construct only via egress gate."""

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


class OpenAICompletionAdapter:
    provider_id = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model_tag: str,
        transport: HttpTransport,
        resilience: ResiliencePolicy,
        base_url: str = "https://api.openai.com/v1",
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
            context_window_tokens=128_000,
            max_output_tokens=4_096,
            embedding_dimensions=None,
            leaves_machine=True,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        if len(request.system) + len(request.user) > _MAX_INPUT_CHARS:
            raise ProviderInputTooLargeError("openai input too large")

        body: dict[str, object] = {
            "model": self._model_tag,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            "max_tokens": request.max_output_tokens,
        }
        if request.json_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "career_assistant_payload",
                    "schema": request.json_schema,
                },
            }

        def _call() -> CompletionResult:
            response = self._transport.request(
                "POST",
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json_body=body,
                timeout_seconds=self._resilience.timeout_seconds,
            )
            classify_http_status(response.status_code)
            data = json.loads(response.body.decode("utf-8"))
            choice = (data.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            text = str(message.get("content") or "")
            if choice.get("finish_reason") == "content_filter" or not text:
                if choice.get("finish_reason") == "content_filter":
                    raise ProviderRefusedError("openai refused the request")
            usage = data.get("usage") or {}
            finish_reason = choice.get("finish_reason")
            return CompletionResult(
                text=text,
                provider_id=self.provider_id,
                model_tag=self._model_tag,
                left_machine=True,
                input_tokens=_int_or_none(usage.get("prompt_tokens")),
                output_tokens=_int_or_none(usage.get("completion_tokens")),
                finish_reason=str(finish_reason) if finish_reason else None,
            )

        return self._resilience.run(_call)


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None
