"""The hermetic tool caller plays a script and records what the loop sent."""

from __future__ import annotations

from career_assistant.application.ports.tool_calling import (
    ChatMessage,
    HermeticToolCaller,
    ToolCall,
    ToolCallingRequest,
    ToolCallingResult,
    ToolDefinition,
)


def _request() -> ToolCallingRequest:
    return ToolCallingRequest(
        system="Answer from tools.",
        messages=(ChatMessage("user", "Which project shows dbt?"),),
        tools=(ToolDefinition("search_evidence", "Search.", {"type": "object"}),),
        max_output_tokens=200,
    )


def test_a_scripted_tool_call_is_returned_and_the_request_is_kept() -> None:
    caller = HermeticToolCaller(
        script=[
            ToolCallingResult(
                content="",
                tool_calls=(ToolCall("c1", "search_evidence", {"query": "dbt"}),),
                provider_id="hermetic",
                model_tag="rules-v1",
            )
        ]
    )

    result = caller.complete(_request())

    assert result.tool_calls[0].name == "search_evidence"
    assert result.tool_calls[0].arguments == {"query": "dbt"}
    assert caller.requests[0].tools[0].name == "search_evidence"


def test_an_exhausted_script_returns_no_tool_call() -> None:
    result = HermeticToolCaller().complete(_request())

    assert result.tool_calls == ()
    assert result.content == ""
