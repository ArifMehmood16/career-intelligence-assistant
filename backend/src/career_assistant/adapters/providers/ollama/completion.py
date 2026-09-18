"""Ollama completion adapter — local HTTP, model tag from configuration."""

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

_MAX_INPUT_CHARS = 100_000


class OllamaCompletionAdapter:
    provider_id = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model_tag: str,
        transport: HttpTransport,
        resilience: ResiliencePolicy,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_tag = model_tag
        self._transport = transport
        self._resilience = resilience

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id=self.provider_id,
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=32_768,
            max_output_tokens=4_096,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        total = len(request.system) + len(request.user)
        if total > _MAX_INPUT_CHARS:
            raise ProviderInputTooLargeError("ollama input too large")

        payload: dict[str, object] = {
            "model": self._model_tag,
            "stream": False,
            "prompt": f"{request.system}\n\n{request.user}",
            "options": {"num_predict": request.max_output_tokens},
        }
        if request.json_schema is not None:
            payload["format"] = "json"

        def _call() -> CompletionResult:
            response = self._transport.request(
                "POST",
                f"{self._base_url}/api/generate",
                json_body=payload,
                timeout_seconds=self._resilience.timeout_seconds,
            )
            classify_http_status(response.status_code)
            data = json.loads(response.body.decode("utf-8"))
            text = str(data.get("response", ""))
            if text.strip().lower().startswith("i cannot"):
                raise ProviderRefusedError("ollama refused the request")
            return CompletionResult(
                text=text,
                provider_id=self.provider_id,
                model_tag=self._model_tag,
                left_machine=False,
                input_tokens=_int_or_none(data.get("prompt_eval_count")),
                output_tokens=_int_or_none(data.get("eval_count")),
            )

        return self._resilience.run(_call)


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None
