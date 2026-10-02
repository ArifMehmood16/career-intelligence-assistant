"""A JSON answer carries the agent's tool steps; stored history carries none."""

from __future__ import annotations

from datetime import UTC, datetime

from career_assistant.api.routes_messages import (
    _assistant_message_wire,
    _history_message_wire,
)
from career_assistant.application.ask.memory import MemoryMessage
from career_assistant.domain.ask import AnswerKind, AnswerResult, ToolStep
from career_assistant.domain.intents import Intent


def _stored() -> MemoryMessage:
    return MemoryMessage(
        id="a-1",
        conversation_id="conv-1",
        author="assistant",
        content="The CV shows it.",
        kind="answer",
        citations=(),
        model="m",
        provider="hermetic",
        left_machine=False,
        client_request_id="cr-1",
        created_at=datetime(2026, 9, 29, tzinfo=UTC),
        workspace_id="ws-1",
    )


def test_the_json_answer_lists_the_tool_steps() -> None:
    result = AnswerResult(
        kind=AnswerKind.ANSWER,
        content="The CV shows it.",
        citations=(),
        intent=Intent.OPEN_QUESTION,
        tool_steps=(ToolStep("search_evidence", (("query", "dbt"),), 2, False),),
    )

    wire = _assistant_message_wire(result=result, answer=_stored())

    assert wire.model_dump(by_alias=True)["toolSteps"] == [
        {
            "name": "search_evidence",
            "arguments": {"query": "dbt"},
            "found": 2,
            "failed": False,
        }
    ]


def test_history_has_no_tool_steps_because_they_are_not_stored() -> None:
    assert _history_message_wire(_stored()).tool_steps == []
