"""Recorded-shape OpenAI transport driven by the hermetic contract builders."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from career_assistant.adapters.providers.hermetic.structured import DEFAULT_BUILDERS
from career_assistant.adapters.providers.http_transport import HttpResponse


@dataclass
class StructuredTransport:
    calls: list[tuple[str, str]] = field(default_factory=list)

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
        assert json_body is not None
        assert "/chat/completions" in url
        response_format = json_body["response_format"]
        assert isinstance(response_format, dict)
        schema_config = response_format["json_schema"]
        assert isinstance(schema_config, dict)
        schema = schema_config["schema"]
        assert isinstance(schema, dict)
        name = schema["title"]
        messages = json_body["messages"]
        assert isinstance(messages, list)
        user = messages[-1]
        assert isinstance(user, dict)
        contract = next(c for c in DEFAULT_BUILDERS if c.__name__ == name)
        payload = DEFAULT_BUILDERS[contract](str(user["content"]))
        body = json.dumps(
            {
                "choices": [
                    {
                        "message": {"content": json.dumps(payload)},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            }
        ).encode()
        return HttpResponse(status_code=200, body=body, headers={})
