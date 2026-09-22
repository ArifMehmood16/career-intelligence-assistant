"""Scripted OpenAI extraction that returns server span-id classifications."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

from tests.support.scripted_transport import ScriptedTransport

from career_assistant.adapters.providers.http_transport import HttpResponse

_SPAN_BLOCK = re.compile(
    r"SPAN (\S+)\nUNTRUSTED_SPAN_BEGIN\n(.*?)\nUNTRUSTED_SPAN_END",
    re.DOTALL,
)


def span_id_extraction_transport() -> ScriptedTransport:
    """Build chat completions that classify the span ids in the prompt."""

    def _payload_for(json_body: Mapping[str, object] | None) -> dict[str, object]:
        messages = []
        if isinstance(json_body, Mapping):
            raw = json_body.get("messages")
            if isinstance(raw, list):
                messages = raw
        user = ""
        for message in messages:
            if isinstance(message, dict) and message.get("role") == "user":
                user = str(message.get("content") or "")
        blocks = list(_SPAN_BLOCK.findall(user))
        if "UNTRUSTED_CV" in user or "UNTRUSTED_COVER_LETTER" in user:
            last_role: str | None = None
            assignments: list[dict[str, object]] = []
            for span, text in blocks:
                if re.search(r"\b(?:19|20)\d{2}\b", text) and "—" in text:
                    last_role = span
                    assignments.append({"spanId": span, "kind": "role_heading"})
                elif last_role is not None and text.lstrip().startswith("-"):
                    assignments.append(
                        {
                            "spanId": span,
                            "kind": "experience",
                            "roleSpanId": last_role,
                        }
                    )
                else:
                    assignments.append({"spanId": span, "kind": "narrative"})
            content: dict[str, object] = {"assignments": assignments}
        elif "REQUIREMENT " in user and "UNTRUSTED_REQUIREMENT" in user:
            req_ids = re.findall(r"^REQUIREMENT (\S+)$", user, re.MULTILINE)
            content = {
                "assessments": [
                    {
                        "requirementId": req_id,
                        "assessment": "missing",
                        "supportingSpanIds": [],
                        "unmetConditions": [],
                        "unknownConditions": [],
                        "contradiction": False,
                        "justification": "No matching evidence in the CV.",
                    }
                    for req_id in req_ids
                ]
            }
        else:
            classifications: list[dict[str, object]] = []
            for span, text in blocks:
                if "must have" in text.lower() or "dbt" in text.lower():
                    kind = "requirement"
                    must_have = True
                    competency = "dbt"
                else:
                    kind = "non_requirement"
                    must_have = False
                    competency = "general"
                classifications.append(
                    {
                        "spanId": span,
                        "item_type": kind,
                        "must_have": must_have,
                        "competency": competency,
                    }
                )
            content = {"classifications": classifications}
        return {
            "choices": [
                {
                    "message": {"content": json.dumps(content)},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 20},
        }

    class _ExtractionTransport(ScriptedTransport):
        def request(
            self,
            method: str,
            url: str,
            *,
            headers: Mapping[str, str] | None = None,
            json_body: Mapping[str, object] | None = None,
            timeout_seconds: float,
        ) -> HttpResponse:
            del headers, timeout_seconds
            self.calls.append((method, url))
            if "/chat/completions" in url:
                return HttpResponse(
                    200, json.dumps(_payload_for(json_body)).encode(), {}
                )
            raise AssertionError(f"no recorded response for {method} {url}")

    return _ExtractionTransport(responses={})
