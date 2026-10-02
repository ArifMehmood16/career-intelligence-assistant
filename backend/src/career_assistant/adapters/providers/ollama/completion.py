"""Ollama completion adapter — local HTTP, model tag from configuration."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from career_assistant.adapters.providers.execution import execution_profile
from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.providers.local_gate import local_call_slot
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
    ModelProfile,
)

# Conservative standalone defaults; production supplies the model catalogue row.
_DEFAULT_PROFILE = ModelProfile(context_window_tokens=32_768, max_output_tokens=4_096)


class OllamaCompletionAdapter:
    provider_id = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model_tag: str,
        transport: HttpTransport,
        resilience: ResiliencePolicy,
        profile: ModelProfile | None = None,
        digest_lookup: Callable[[], str | None] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_tag = model_tag
        self._transport = transport
        self._resilience = resilience
        self._profile = profile or _DEFAULT_PROFILE
        self._digest_lookup = digest_lookup
        self._digest: str | None = None

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
            leaves_machine=False,
            execution=execution_profile(self._profile),
            supports_tool_calling=self._profile.supports_tool_calling,
            supports_prompt_caching=self._profile.supports_prompt_caching,
            supports_temperature=self._profile.supports_temperature,
            supports_seed=self._profile.supports_seed,
            model_digest=self._model_digest(),
        )

    def _model_digest(self) -> str | None:
        """Looked up until found, then kept: a failed lookup is tried again."""
        if self._digest is None and self._digest_lookup is not None:
            self._digest = self._digest_lookup()
        return self._digest

    def complete(self, request: CompletionRequest) -> CompletionResult:
        total = len(request.system) + len(request.user)
        if (
            total + 3
        ) // 4 + request.max_output_tokens > self._profile.context_window_tokens:
            raise ProviderInputTooLargeError("ollama input too large")

        payload: dict[str, object] = {
            "model": self._model_tag,
            "stream": False,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            "options": self._options(request),
        }
        if request.json_schema is not None:
            # The schema is the structured-output contract. "json" alone only
            # constrains syntax, so item_type enum descriptions never reach
            # the local model.
            payload["format"] = request.json_schema

        def _call() -> CompletionResult:
            response = self._transport.request(
                "POST",
                f"{self._base_url}/api/chat",
                json_body=payload,
                timeout_seconds=self._resilience.timeout_seconds,
            )
            classify_http_status(response.status_code, response.headers)
            data = json.loads(response.body.decode("utf-8"))
            message = data.get("message") or {}
            text = str(message.get("content", "")) if isinstance(message, dict) else ""
            if text.strip().lower().startswith("i cannot"):
                raise ProviderRefusedError("ollama refused the request")
            return CompletionResult(
                text=text,
                provider_id=self.provider_id,
                model_tag=self._model_tag,
                left_machine=False,
                input_tokens=_int_or_none(data.get("prompt_eval_count")),
                output_tokens=_int_or_none(data.get("eval_count")),
                finish_reason=_str_or_none(data.get("done_reason")),
            )

        with local_call_slot(
            self.provider_id,
            self._model_tag,
            operation="completion",
            max_in_flight=self._profile.completion_concurrency,
        ):
            return self._resilience.run(_call)

    def _options(self, request: CompletionRequest) -> dict[str, object]:
        # num_ctx is explicit: without it Ollama uses its server default and cuts a
        # long prompt without an error, whatever the descriptor reports.
        options: dict[str, object] = {
            "num_ctx": self._profile.context_window_tokens,
            "num_predict": request.max_output_tokens,
        }
        if request.temperature is not None and self._profile.supports_temperature:
            options["temperature"] = request.temperature
        if request.seed is not None and self._profile.supports_seed:
            options["seed"] = request.seed
        return options


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _str_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
