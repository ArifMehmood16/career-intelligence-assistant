"""The provider factory builds every adapter with its catalogue profile (PLAN 18.1)."""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from tests.support.scripted_transport import ScriptedTransport

from career_assistant.adapters.providers.factory import (
    build_completion_port,
    build_embedding_port,
)
from career_assistant.application.providers.model_catalogue import load_model_catalogue
from career_assistant.settings import ProviderSettings

_CATALOGUE = load_model_catalogue(
    Path(__file__).resolve().parents[3] / "config" / "models.toml"
)


def _settings(**overrides: object) -> ProviderSettings:
    return ProviderSettings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_ollama_completion_reports_its_catalogue_row() -> None:
    port = build_completion_port(
        _settings(completion_provider="ollama", ollama_completion_model="qwen2.5:7b"),
        transport=ScriptedTransport({}),
    )

    expected = _CATALOGUE.profile("ollama", "qwen2.5:7b")
    assert port.capabilities.context_window_tokens == expected.context_window_tokens
    assert port.capabilities.max_output_tokens == expected.max_output_tokens
    assert port.capabilities.supports_tool_calling is expected.supports_tool_calling


def test_an_unnamed_ollama_tag_gets_the_provider_defaults() -> None:
    port = build_completion_port(
        _settings(completion_provider="ollama"),
        transport=ScriptedTransport({}),
        model_tag="a-model-nobody-listed",
    )

    expected = _CATALOGUE.profile("ollama", "a-model-nobody-listed")
    assert port.capabilities.context_window_tokens == expected.context_window_tokens


def test_hosted_completion_reports_its_catalogue_row() -> None:
    port = build_completion_port(
        _settings(
            completion_provider="openai",
            allow_hosted_providers=True,
            openai_api_key=SecretStr("test-key"),
            openai_completion_model="gpt-4o-mini",
        ),
        transport=ScriptedTransport({}),
    )

    expected = _CATALOGUE.profile("openai", "gpt-4o-mini")
    assert port.capabilities.max_output_tokens == expected.max_output_tokens
    assert port.capabilities.supports_seed is expected.supports_seed


def test_embedding_ports_report_their_catalogue_row() -> None:
    port = build_embedding_port(
        _settings(
            embedding_provider="ollama", ollama_embedding_model="nomic-embed-text"
        ),
        transport=ScriptedTransport({}),
    )

    expected = _CATALOGUE.profile("ollama", "nomic-embed-text")
    assert port.capabilities.context_window_tokens == expected.context_window_tokens
