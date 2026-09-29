"""Structured-output ports for a chosen provider (PLAN 18.10).

A model provider's completion port is decorated by the caller (call accounting)
and then wrapped for schema validation and one repair. The hermetic fixture
builds each v2 contract from rules instead, because its plain completion
adapter answers in prose.
"""

from __future__ import annotations

from collections.abc import Callable

from career_assistant.adapters.providers.factory import build_completion_port
from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.structured import StructuredCompletionPort
from career_assistant.application.providers.structured import StructuredCompleter
from career_assistant.settings import ProviderSettings

HERMETIC = "hermetic"


def _unchanged(port: CompletionPort) -> CompletionPort:
    return port


def build_structured_port(
    settings: ProviderSettings,
    *,
    provider_id: str,
    model_tag: str,
    transport: HttpTransport | None = None,
    wrap: Callable[[CompletionPort], CompletionPort] = _unchanged,
) -> StructuredCompletionPort:
    if provider_id == HERMETIC:
        return HermeticStructuredCompleter()
    completion = build_completion_port(
        settings, transport=transport, provider_id=provider_id, model_tag=model_tag
    )
    return StructuredCompleter(wrap(completion))
