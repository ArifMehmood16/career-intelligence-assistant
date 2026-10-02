"""OpenAI chat completions adapter — hosted; construct only via egress gate."""

from __future__ import annotations

import json
from typing import Any

from career_assistant.adapters.providers.call_gate import (
    HostedCallGate,
    RateLimitNote,
    estimate_tokens,
    run_hosted,
)
from career_assistant.adapters.providers.execution import execution_profile
from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.providers.openai.errors import classify_openai_response
from career_assistant.adapters.providers.resilience import ResiliencePolicy
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

# Conservative standalone defaults; production supplies the model catalogue row.
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
        gate: HostedCallGate | None = None,
    ) -> None:
        self._api_key = api_key
        self._model_tag = model_tag
        self._transport = transport
        self._resilience = resilience
        self._profile = profile or _DEFAULT_PROFILE
        self._base_url = base_url.rstrip("/")
        self._gate = gate

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
            execution=execution_profile(self._profile),
            supports_tool_calling=self._profile.supports_tool_calling,
            supports_prompt_caching=self._profile.supports_prompt_caching,
            supports_temperature=self._profile.supports_temperature,
            supports_seed=self._profile.supports_seed,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        if (
            len(request.system) + len(request.user) + 3
        ) // 4 + request.max_output_tokens > self._profile.context_window_tokens:
            raise ProviderInputTooLargeError("openai input too large")

        body = self._body(request)

        def _call(note: RateLimitNote) -> CompletionResult:
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
            if response.status_code >= 400:
                note(response.headers)
            classify_openai_response(
                response, model_tag=self._model_tag, operation="completion"
            )
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
            prompt_tokens = _int_or_none(usage.get("prompt_tokens"))
            completion_tokens = _int_or_none(usage.get("completion_tokens"))
            note(response.headers, used_tokens=_sum(prompt_tokens, completion_tokens))
            return CompletionResult(
                text=text,
                provider_id=self.provider_id,
                model_tag=self._model_tag,
                left_machine=True,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                finish_reason=str(finish_reason) if finish_reason else None,
            )

        return run_hosted(
            self._gate,
            provider_id=self.provider_id,
            model_tag=self._model_tag,
            estimated_tokens=estimate_tokens(
                len(request.system) + len(request.user), request.max_output_tokens
            ),
            resilience=self._resilience,
            operation=_call,
        )

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


def _sum(left: int | None, right: int | None) -> int | None:
    if left is None and right is None:
        return None
    return (left or 0) + (right or 0)
