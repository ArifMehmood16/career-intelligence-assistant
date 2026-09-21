"""Hermetic completion — rule-based, no network, no keys."""

from __future__ import annotations

import json
import re
from typing import Any

from career_assistant.application.ports.errors import (
    ProviderInputTooLargeError,
    ProviderRefusedError,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)

_REFUSAL_MARKERS = ("refuse to answer", "i cannot assist", "[refuse]")
_MAX_INPUT_CHARS = 20_000
_DIM_CONTEXT = 8_192
_DIM_OUTPUT = 1_024


class HermeticCompletionAdapter:
    provider_id = "hermetic"
    model_tag = "rules-v1"

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id=self.provider_id,
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=_DIM_CONTEXT,
            max_output_tokens=_DIM_OUTPUT,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        total = len(request.system) + len(request.user)
        if total > _MAX_INPUT_CHARS or request.max_output_tokens < 1:
            raise ProviderInputTooLargeError(
                f"input of {total} characters exceeds hermetic limit {_MAX_INPUT_CHARS}"
            )
        lowered = f"{request.system}\n{request.user}".lower()
        if any(marker in lowered for marker in _REFUSAL_MARKERS):
            raise ProviderRefusedError("hermetic adapter refused the request")

        if request.json_schema is not None:
            text = json.dumps(
                _structured_from_schema(request.json_schema, request.user),
                ensure_ascii=True,
                sort_keys=True,
            )
        else:
            text = _phrase(request.user)

        if len(text) > request.max_output_tokens * 4:
            text = text[: request.max_output_tokens * 4]

        return CompletionResult(
            text=text,
            provider_id=self.provider_id,
            model_tag=self.model_tag,
            left_machine=False,
            input_tokens=_estimate_tokens(request.system + request.user),
            output_tokens=_estimate_tokens(text),
            fallback_used=False,
            latency_ms=0,
        )


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _phrase(user: str) -> str:
    compact = " ".join(user.split())
    if not compact:
        return "Not enough evidence."
    return f"Based on the supplied text: {compact}"


def _structured_from_schema(schema: dict[str, Any], user: str) -> dict[str, Any]:
    """Deterministic stand-in for structured extraction."""
    requirements = _extract_requirement_lines(user)
    properties = schema.get("properties")
    if isinstance(properties, dict) and "requirements" in properties:
        return {
            "requirements": [
                {
                    "quote": item,
                    "text": item,
                    "must_have": True,
                    "item_type": "requirement",
                }
                for item in requirements
            ]
        }
    if isinstance(properties, dict) and "roles" in properties:
        return {
            "roles": [
                {
                    "employer": "",
                    "title": "",
                    "date_range_quote": "",
                    "claims": [
                        {
                            "quote": item,
                            "competency": "general",
                            "scope": "",
                            "technologies": [],
                            "outcome": "",
                        }
                        for item in requirements
                    ],
                }
            ]
        }
    if isinstance(properties, dict) and "claims" in properties:
        return {"claims": [{"text": item} for item in requirements]}
    return {"items": requirements}


_BULLET = re.compile(r"^\s*[-*•]\s+(.+)$")


def _extract_requirement_lines(text: str) -> list[str]:
    found: list[str] = []
    for line in text.splitlines():
        match = _BULLET.match(line)
        if match:
            found.append(match.group(1).strip())
    if not found:
        stripped = " ".join(text.split())
        if stripped:
            found.append(stripped[:200])
    return found
