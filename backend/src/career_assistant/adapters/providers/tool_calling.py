"""Tool-calling adapters. One vendor's request shape, the same port result.

Recorded replies drive the contract suite. No adapter is called unless the
model's capability descriptor reports tool calling, and a hosted one is
constructible only through the egress gate.
"""

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
from career_assistant.adapters.providers.local_gate import local_call_slot
from career_assistant.adapters.providers.openai.errors import classify_openai_response
from career_assistant.adapters.providers.resilience import (
    ResiliencePolicy,
    classify_http_status,
)
from career_assistant.application.ports.errors import (
    ProviderInputTooLargeError,
    ProviderRefusedError,
)
from career_assistant.application.ports.tool_calling import (
    ChatMessage,
    ToolCall,
    ToolCallingRequest,
    ToolCallingResult,
    ToolDefinition,
)
from career_assistant.application.ports.types import CapabilityDescriptor, ModelProfile

_DEFAULT_PROFILE = ModelProfile(context_window_tokens=8_192, max_output_tokens=2_000)


def _arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    if isinstance(value, str) and value.strip():
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return {str(key): item for key, item in parsed.items()}
    return {}


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return int(value)


def _too_large(request: ToolCallingRequest, profile: ModelProfile) -> bool:
    size = len(request.system) + sum(
        len(message.content) for message in request.messages
    )
    size += sum(
        len(json.dumps(tool.parameters)) + len(tool.description)
        for tool in request.tools
    )
    return (size + 3) // 4 + request.max_output_tokens > profile.context_window_tokens


def _capabilities(
    provider_id: str, profile: ModelProfile, *, leaves_machine: bool
) -> CapabilityDescriptor:
    return CapabilityDescriptor(
        provider_id=provider_id,
        supports_completion=True,
        supports_embedding=False,
        supports_structured_output=True,
        context_window_tokens=profile.context_window_tokens,
        max_output_tokens=profile.max_output_tokens,
        embedding_dimensions=None,
        leaves_machine=leaves_machine,
        execution=execution_profile(profile),
        supports_tool_calling=True,
        supports_prompt_caching=profile.supports_prompt_caching,
        supports_temperature=profile.supports_temperature,
        supports_seed=profile.supports_seed,
    )


def _tools_openai(tools: tuple[ToolDefinition, ...]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tools
    ]


def _messages_openai(request: ToolCallingRequest) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": request.system}]
    for message in request.messages:
        messages.append(_openai_message(message))
    return messages


def _openai_message(message: ChatMessage) -> dict[str, Any]:
    if message.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": message.call_id,
            "content": message.content,
        }
    if message.tool_calls:
        return {
            "role": "assistant",
            "content": message.content or None,
            "tool_calls": [
                {
                    "id": call.call_id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments),
                    },
                }
                for call in message.tool_calls
            ],
        }
    return {"role": message.role, "content": message.content}


def _calls_from_openai(message: dict[str, Any]) -> tuple[ToolCall, ...]:
    calls: list[ToolCall] = []
    for index, raw in enumerate(message.get("tool_calls") or []):
        function = raw.get("function") or {}
        calls.append(
            ToolCall(
                call_id=str(raw.get("id") or f"call-{index}"),
                name=str(function.get("name") or ""),
                arguments=_arguments(function.get("arguments")),
            )
        )
    return tuple(calls)


class OllamaToolCaller:
    provider_id = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model_tag: str,
        transport: HttpTransport,
        resilience: ResiliencePolicy,
        profile: ModelProfile | None = None,
    ) -> None:
        self._model_tag = model_tag
        self._transport = transport
        self._resilience = resilience
        self._profile = profile or _DEFAULT_PROFILE
        self._url = f"{base_url.rstrip('/')}/api/chat"

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return _capabilities(self.provider_id, self._profile, leaves_machine=False)

    def complete(self, request: ToolCallingRequest) -> ToolCallingResult:
        if _too_large(request, self._profile):
            raise ProviderInputTooLargeError("ollama input too large")
        body = {
            "model": self._model_tag,
            "stream": False,
            "messages": _messages_ollama(request),
            "tools": _tools_openai(request.tools),
            "options": {
                "num_predict": request.max_output_tokens,
                "num_ctx": self._profile.context_window_tokens,
            },
        }
        with local_call_slot(
            self.provider_id,
            self._model_tag,
            operation="completion",
            max_in_flight=self._profile.completion_concurrency,
        ):
            return self._resilience.run(lambda: self._call(body))

    def _call(self, body: dict[str, Any]) -> ToolCallingResult:
        response = self._transport.request(
            "POST",
            self._url,
            headers={"Content-Type": "application/json"},
            json_body=body,
            timeout_seconds=self._resilience.timeout_seconds,
        )
        classify_http_status(response.status_code, response.headers)
        data = json.loads(response.body.decode("utf-8"))
        message = data.get("message") or {}
        return ToolCallingResult(
            content=str(message.get("content") or ""),
            tool_calls=_calls_from_ollama(message),
            provider_id=self.provider_id,
            model_tag=self._model_tag,
            left_machine=False,
            input_tokens=_int_or_none(data.get("prompt_eval_count")),
            output_tokens=_int_or_none(data.get("eval_count")),
        )


def _messages_ollama(request: ToolCallingRequest) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": request.system}]
    for message in request.messages:
        if message.role == "tool":
            messages.append(
                {
                    "role": "tool",
                    "content": message.content,
                    "tool_name": message.name,
                }
            )
        elif message.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "function": {
                                "name": call.name,
                                "arguments": call.arguments,
                            }
                        }
                        for call in message.tool_calls
                    ],
                }
            )
        else:
            messages.append({"role": message.role, "content": message.content})
    return messages


def _calls_from_ollama(message: dict[str, Any]) -> tuple[ToolCall, ...]:
    calls: list[ToolCall] = []
    for index, raw in enumerate(message.get("tool_calls") or []):
        function = raw.get("function") or {}
        calls.append(
            ToolCall(
                call_id=f"call-{index}",
                name=str(function.get("name") or ""),
                arguments=_arguments(function.get("arguments")),
            )
        )
    return tuple(calls)


class OpenAIToolCaller:
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
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._gate = gate

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return _capabilities(self.provider_id, self._profile, leaves_machine=True)

    def complete(self, request: ToolCallingRequest) -> ToolCallingResult:
        if _too_large(request, self._profile):
            raise ProviderInputTooLargeError("openai input too large")
        body: dict[str, Any] = {
            "model": self._model_tag,
            "messages": _messages_openai(request),
            "tools": _tools_openai(request.tools),
            "max_completion_tokens": request.max_output_tokens,
        }
        if not request.tools:
            body.pop("tools")
        return run_hosted(
            self._gate,
            provider_id=self.provider_id,
            model_tag=self._model_tag,
            estimated_tokens=_estimate(request),
            resilience=self._resilience,
            operation=lambda note: self._call(body, note),
        )

    def _call(self, body: dict[str, Any], note: RateLimitNote) -> ToolCallingResult:
        response = self._transport.request(
            "POST",
            self._url,
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
            response, model_tag=self._model_tag, operation="tool_calling"
        )
        data = json.loads(response.body.decode("utf-8"))
        choice = (data.get("choices") or [{}])[0]
        if choice.get("finish_reason") == "content_filter":
            raise ProviderRefusedError("openai refused the request")
        message = choice.get("message") or {}
        usage = data.get("usage") or {}
        note(
            response.headers,
            used_tokens=_used(usage, "prompt_tokens", "completion_tokens"),
        )
        return ToolCallingResult(
            content=str(message.get("content") or ""),
            tool_calls=_calls_from_openai(message),
            provider_id=self.provider_id,
            model_tag=self._model_tag,
            left_machine=True,
            input_tokens=_int_or_none(usage.get("prompt_tokens")),
            output_tokens=_int_or_none(usage.get("completion_tokens")),
        )


class AnthropicToolCaller:
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
        gate: HostedCallGate | None = None,
    ) -> None:
        self._api_key = api_key
        self._model_tag = model_tag
        self._transport = transport
        self._resilience = resilience
        self._profile = profile or _DEFAULT_PROFILE
        self._url = f"{base_url.rstrip('/')}/messages"
        self._gate = gate

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return _capabilities(self.provider_id, self._profile, leaves_machine=True)

    def complete(self, request: ToolCallingRequest) -> ToolCallingResult:
        if _too_large(request, self._profile):
            raise ProviderInputTooLargeError("anthropic input too large")
        body: dict[str, Any] = {
            "model": self._model_tag,
            "system": request.system,
            "messages": _messages_anthropic(request.messages),
            "max_tokens": request.max_output_tokens,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in request.tools
            ],
        }
        return run_hosted(
            self._gate,
            provider_id=self.provider_id,
            model_tag=self._model_tag,
            estimated_tokens=_estimate(request),
            resilience=self._resilience,
            operation=lambda note: self._call(body, note),
        )

    def _call(self, body: dict[str, Any], note: RateLimitNote) -> ToolCallingResult:
        response = self._transport.request(
            "POST",
            self._url,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json_body=body,
            timeout_seconds=self._resilience.timeout_seconds,
        )
        if response.status_code >= 400:
            note(response.headers)
        classify_http_status(response.status_code, response.headers)
        data = json.loads(response.body.decode("utf-8"))
        if data.get("stop_reason") == "refusal":
            raise ProviderRefusedError("anthropic refused the request")
        blocks = data.get("content") or []
        text = "".join(
            str(block.get("text", ""))
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        )
        usage = data.get("usage") or {}
        note(
            response.headers,
            used_tokens=_used(usage, "input_tokens", "output_tokens"),
        )
        return ToolCallingResult(
            content=text,
            tool_calls=_calls_from_anthropic(blocks),
            provider_id=self.provider_id,
            model_tag=self._model_tag,
            left_machine=True,
            input_tokens=_int_or_none(usage.get("input_tokens")),
            output_tokens=_int_or_none(usage.get("output_tokens")),
        )


def _messages_anthropic(messages: tuple[ChatMessage, ...]) -> list[dict[str, Any]]:
    built: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []

    def flush() -> None:
        if pending:
            built.append({"role": "user", "content": list(pending)})
            pending.clear()

    for message in messages:
        if message.role == "tool":
            pending.append(
                {
                    "type": "tool_result",
                    "tool_use_id": message.call_id,
                    "content": message.content,
                }
            )
            continue
        flush()
        if message.tool_calls:
            content: list[dict[str, Any]] = []
            if message.content:
                content.append({"type": "text", "text": message.content})
            for call in message.tool_calls:
                content.append(
                    {
                        "type": "tool_use",
                        "id": call.call_id,
                        "name": call.name,
                        "input": call.arguments,
                    }
                )
            built.append({"role": "assistant", "content": content})
        else:
            built.append({"role": message.role, "content": message.content})
    flush()
    return built


def _calls_from_anthropic(blocks: list[Any]) -> tuple[ToolCall, ...]:
    calls: list[ToolCall] = []
    for index, block in enumerate(blocks):
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        calls.append(
            ToolCall(
                call_id=str(block.get("id") or f"call-{index}"),
                name=str(block.get("name") or ""),
                arguments=_arguments(block.get("input")),
            )
        )
    return tuple(calls)


def _estimate(request: ToolCallingRequest) -> int:
    chars = len(request.system) + sum(
        len(message.content) for message in request.messages
    )
    return estimate_tokens(chars, request.max_output_tokens)


def _used(usage: dict[str, Any], left: str, right: str) -> int | None:
    prompt = _int_or_none(usage.get(left))
    completion = _int_or_none(usage.get(right))
    if prompt is None and completion is None:
        return None
    return (prompt or 0) + (completion or 0)
