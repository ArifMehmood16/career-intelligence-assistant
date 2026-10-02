"""PLAN 18.10 — v2 model calls get a structured port for the chosen provider."""

from __future__ import annotations

from tests.support.scripted_transport import ScriptedTransport

from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.adapters.providers.structured_factory import (
    build_structured_port,
)
from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.providers.structured import StructuredCompleter
from career_assistant.settings import ProviderSettings

SETTINGS = ProviderSettings(
    completion_provider="hermetic", embedding_provider="hermetic"
)


def test_the_hermetic_fixture_answers_every_v2_contract_itself() -> None:
    port = build_structured_port(SETTINGS, provider_id="hermetic", model_tag="rules-v1")

    assert isinstance(port, HermeticStructuredCompleter)


def test_a_model_provider_is_wrapped_after_the_caller_decorates_it() -> None:
    wrapped: list[CompletionPort] = []

    def record(port: CompletionPort) -> CompletionPort:
        wrapped.append(port)
        return port

    port = build_structured_port(
        SETTINGS,
        provider_id="ollama",
        model_tag="qwen3:8b",
        transport=ScriptedTransport({}),
        wrap=record,
    )

    assert isinstance(port, StructuredCompleter)
    assert len(wrapped) == 1
