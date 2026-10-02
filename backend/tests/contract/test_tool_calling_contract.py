"""Every tool-calling adapter returns the same call from its own recorded reply.

No network. Hermetic plays a script; the HTTP adapters parse a fixture body.
"""

from __future__ import annotations

import json

import pytest
from tests.support.recording_transport import RecordingTransport

from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
)
from career_assistant.adapters.providers.tool_calling import (
    AnthropicToolCaller,
    OllamaToolCaller,
    OpenAIToolCaller,
)
from career_assistant.application.ports.tool_calling import (
    ChatMessage,
    HermeticToolCaller,
    ToolCall,
    ToolCallingPort,
    ToolCallingRequest,
    ToolCallingResult,
    ToolDefinition,
)

_TOOL = ToolDefinition("search_evidence", "Search the CV.", {"type": "object"})
_QUERY = {"query": "dbt"}
_ANSWER = '{"answer":"Owned dbt models.","citations":[],"support":"grounded"}'


def _resilience() -> ResiliencePolicy:
    return ResiliencePolicy(
        timeout_seconds=1.0,
        max_retries=0,
        breaker=CircuitBreaker(5),
        sleep=lambda _seconds: None,
    )


def _request() -> ToolCallingRequest:
    return ToolCallingRequest(
        system="Answer from tools.",
        messages=(
            ChatMessage("user", "Where is dbt?"),
            ChatMessage(
                "assistant",
                "",
                tool_calls=(ToolCall("c1", "search_evidence", _QUERY),),
            ),
            ChatMessage(
                "tool", "Owned dbt models.", call_id="c1", name="search_evidence"
            ),
        ),
        tools=(_TOOL,),
        max_output_tokens=200,
    )


def _ollama(payload: dict[str, object]) -> tuple[ToolCallingPort, RecordingTransport]:
    transport = RecordingTransport(payload)
    return (
        OllamaToolCaller(
            base_url="http://ollama.test",
            model_tag="m",
            transport=transport,
            resilience=_resilience(),
        ),
        transport,
    )


def _openai(payload: dict[str, object]) -> tuple[ToolCallingPort, RecordingTransport]:
    transport = RecordingTransport(payload)
    return (
        OpenAIToolCaller(
            api_key="k",
            model_tag="m",
            transport=transport,
            resilience=_resilience(),
        ),
        transport,
    )


def _anthropic(
    payload: dict[str, object],
) -> tuple[ToolCallingPort, RecordingTransport]:
    transport = RecordingTransport(payload)
    return (
        AnthropicToolCaller(
            api_key="k",
            model_tag="m",
            transport=transport,
            resilience=_resilience(),
        ),
        transport,
    )


def _hermetic(result: ToolCallingResult) -> ToolCallingPort:
    return HermeticToolCaller(script=[result])


_CALL_BODIES = {
    "ollama": {
        "message": {
            "content": "",
            "tool_calls": [
                {"function": {"name": "search_evidence", "arguments": _QUERY}}
            ],
        }
    },
    "openai": {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "search_evidence",
                                "arguments": json.dumps(_QUERY),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4},
    },
    "anthropic": {
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_1",
                "name": "search_evidence",
                "input": _QUERY,
            }
        ],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 10, "output_tokens": 4},
    },
}

_TEXT_BODIES = {
    "ollama": {
        "message": {"content": _ANSWER},
        "prompt_eval_count": 12,
        "eval_count": 8,
    },
    "openai": {
        "choices": [{"message": {"content": _ANSWER}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 8},
    },
    "anthropic": {
        "content": [{"type": "text", "text": _ANSWER}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 12, "output_tokens": 8},
    },
}

_BUILDERS = {"ollama": _ollama, "openai": _openai, "anthropic": _anthropic}


@pytest.mark.parametrize("vendor", ["hermetic", "ollama", "openai", "anthropic"])
def test_each_adapter_returns_the_same_tool_call(vendor: str) -> None:
    if vendor == "hermetic":
        port: ToolCallingPort = _hermetic(
            ToolCallingResult(
                content="",
                tool_calls=(ToolCall("c1", "search_evidence", _QUERY),),
                provider_id="hermetic",
                model_tag="rules-v1",
            )
        )
    else:
        port, _transport = _BUILDERS[vendor](_CALL_BODIES[vendor])

    result = port.complete(_request())

    assert [(call.name, call.arguments) for call in result.tool_calls] == [
        ("search_evidence", _QUERY)
    ]
    assert port.capabilities.supports_tool_calling is True


@pytest.mark.parametrize("vendor", ["ollama", "openai", "anthropic"])
def test_each_adapter_returns_the_same_final_text(vendor: str) -> None:
    port, transport = _BUILDERS[vendor](_TEXT_BODIES[vendor])

    result = port.complete(_request())

    assert result.content == _ANSWER
    assert result.tool_calls == ()
    assert result.input_tokens == 12
    sent = json.dumps(transport.last.body)
    assert "search_evidence" in sent
    assert "Owned dbt models." in sent
