"""SSE framing for AskEvent — transport only, no second ask implementation."""

from __future__ import annotations

import json

from career_assistant.application.ask.service import AskEvent


def format_ask_sse(event: AskEvent) -> str:
    """Render one SSE event block matching docs/api-contract.md."""
    if event.type == "meta":
        data: dict[str, object] = {
            "questionId": event.question_id,
            "messageId": event.message_id,
            "intent": None if event.intent is None else event.intent.value,
            "provider": event.provider,
            "model": event.model,
        }
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
