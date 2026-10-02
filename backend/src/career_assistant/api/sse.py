"""SSE framing for AskEvent — transport only, no second ask implementation."""

from __future__ import annotations

import json

from career_assistant.application.ask.service import AskEvent
from career_assistant.domain.ask import ToolStep


def tool_steps_payload(steps: tuple[ToolStep, ...]) -> list[dict[str, object]]:
    """The agent's tool calls as the browser shows them; shared with the JSON route."""
    return [
        {
            "name": step.name,
            "arguments": dict(step.arguments),
            "found": step.found,
            "failed": step.failed,
        }
        for step in steps
    ]


def format_ask_sse(event: AskEvent) -> str:
    """Render one SSE event block matching docs/api-contract.md."""
    if event.type == "meta":
        data: dict[str, object] = {
            "questionId": event.question_id,
            "messageId": event.message_id,
            "intent": None if event.intent is None else event.intent.value,
            "provider": event.provider,
            "model": event.model,
            "leftMachine": bool(event.left_machine),
        }
    elif event.type == "tools":
        data = {"steps": tool_steps_payload(event.tool_steps or ())}
    elif event.type == "token":
        data = {"text": event.text or ""}
    elif event.type == "citations":
        data = {
            "citations": [
                {"id": citation.span_id, "label": citation.label}
                for citation in (event.citations or ())
            ]
        }
    elif event.type == "done":
        data = {"kind": event.kind}
    elif event.type == "error":
        data = {
            "code": event.kind or "provider_failed",
            "message": event.text or "Provider failed.",
        }
    else:
        data = {}
    return f"event: {event.type}\ndata: {json.dumps(data)}\n\n"
