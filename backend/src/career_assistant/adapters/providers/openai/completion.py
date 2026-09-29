"""OpenAI chat completions adapter — hosted; construct only via egress gate."""

from __future__ import annotations

import json
from typing import Any

from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.providers.resilience import (
    ResiliencePolicy,
    classify_http_status,
)
from career_assistant.adapters.providers.schema_dialects import (
    drop_strict_mode_nulls,
    openai_strict_schema,
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
_DEFAULT_PROFILE = ModelProfile(context_window_tokens=128_000, max_output_tokens=4_096)


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
            raise ProviderInputTooLargeError("openai input too large")

        body = self._body(request)

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
            if (
                request.json_schema is not None
                and self._profile.native_structured_output
            ):
                text = drop_strict_mode_nulls(text, request.json_schema)
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

    def _json_schema(self, schema: dict[str, Any]) -> dict[str, object]:
        if not self._profile.native_structured_output:
            return {"name": "career_assistant_payload", "schema": schema}
        return {
            "name": "career_assistant_payload",
            "strict": True,
            "schema": openai_strict_schema(schema),
        }

    def _body(self, request: CompletionRequest) -> dict[str, object]:
        body: dict[str, object] = {
            "model": self._model_tag,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            # max_tokens is deprecated and rejected by reasoning models.
            "max_completion_tokens": request.max_output_tokens,
        }
        if request.json_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": self._json_schema(request.json_schema),
            }
        if request.temperature is not None and self._profile.supports_temperature:
            body["temperature"] = request.temperature
        if request.seed is not None and self._profile.supports_seed:
            body["seed"] = request.seed
        return body


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None
