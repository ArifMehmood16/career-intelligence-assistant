"""Model limits and capabilities come from configuration, not adapter constants.

PLAN 18.1: capability descriptors read context window and output limits from a
per-model configuration table. A tag the table does not name falls back to its
provider's defaults, field by field.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from career_assistant.application.providers.model_catalogue import (
    ModelCatalogue,
    ModelCatalogueError,
    load_model_catalogue,
)
from career_assistant.settings import ProviderSettings

_REPO_CATALOGUE = Path(__file__).resolve().parents[3] / "config" / "models.toml"

_CATALOGUE = """
version = "model-catalogue-test"

[defaults.ollama]
context_window_tokens = 8192
max_output_tokens = 2048
supports_tool_calling = false
supports_prompt_caching = false
supports_temperature = true
supports_seed = true

[models.ollama."big-model:1b"]
context_window_tokens = 65536
max_output_tokens = 16384
supports_tool_calling = true

[models.ollama."embedder"]
context_window_tokens = 2048
embedding_query_prefix = "search_query: "
embedding_document_prefix = "search_document: "
"""


def _catalogue(tmp_path: Path) -> ModelCatalogue:
    path = tmp_path / "models.toml"
    path.write_text(_CATALOGUE, encoding="utf-8")
    return load_model_catalogue(path)


def test_a_named_model_uses_its_own_row(tmp_path: Path) -> None:
    profile = _catalogue(tmp_path).profile("ollama", "big-model:1b")

    assert profile.context_window_tokens == 65_536
    assert profile.max_output_tokens == 16_384
    assert profile.supports_tool_calling is True


def test_a_row_overrides_provider_defaults_field_by_field(tmp_path: Path) -> None:
    profile = _catalogue(tmp_path).profile("ollama", "big-model:1b")

    assert profile.supports_prompt_caching is False
    assert profile.supports_temperature is True
    assert profile.supports_seed is True


def test_an_unnamed_tag_falls_back_to_its_provider_defaults(tmp_path: Path) -> None:
    profile = _catalogue(tmp_path).profile("ollama", "some-other-model")

    assert profile.context_window_tokens == 8_192
    assert profile.max_output_tokens == 2_048
    assert profile.supports_tool_calling is False
    assert profile.embedding_query_prefix == ""


def test_embedding_prefixes_are_model_configuration(tmp_path: Path) -> None:
    profile = _catalogue(tmp_path).profile("ollama", "embedder")

    assert profile.embedding_query_prefix == "search_query: "
    assert profile.embedding_document_prefix == "search_document: "


def test_a_provider_with_no_defaults_is_a_configuration_error(tmp_path: Path) -> None:
    with pytest.raises(ModelCatalogueError):
        _catalogue(tmp_path).profile("unknown-vendor", "anything")


def test_the_catalogue_version_is_recorded(tmp_path: Path) -> None:
    assert _catalogue(tmp_path).version == "model-catalogue-test"


def test_the_repository_catalogue_names_every_default_model_tag() -> None:
    catalogue = load_model_catalogue(_REPO_CATALOGUE)
    settings = ProviderSettings(_env_file=None)

    configured = {
        ("ollama", settings.ollama_completion_model),
        ("ollama", settings.ollama_embedding_model),
        ("openai", settings.openai_completion_model),
        ("openai", settings.openai_embedding_model),
        ("anthropic", settings.anthropic_completion_model),
    }
    for provider_id, model_tag in configured:
        assert catalogue.names(provider_id, model_tag), (provider_id, model_tag)


@pytest.mark.parametrize(
    "row",
    [
        pytest.param("max_output_tokens = 10\n", id="missing-context-window"),
        pytest.param(
            'context_window_tokens = "big"\nmax_output_tokens = 10\n', id="wrong-type"
        ),
        pytest.param(
            'context_window_tokens = 10\nmax_output_tokens = 10\ncolour = "blue"\n',
            id="unknown-field",
        ),
    ],
)
def test_a_malformed_row_is_a_configuration_error(tmp_path: Path, row: str) -> None:
    path = tmp_path / "models.toml"
    path.write_text(f'version = "v"\n\n[defaults.ollama]\n{row}', encoding="utf-8")

    with pytest.raises(ModelCatalogueError):
        load_model_catalogue(path).profile("ollama", "any")


def test_native_structured_output_is_a_per_model_flag() -> None:
    catalogue = load_model_catalogue(_REPO_CATALOGUE)

    # Anthropic lists Sonnet 4.5 and later, not Sonnet 4, for structured outputs.
    assert (
        catalogue.profile("anthropic", "claude-sonnet-4-0").native_structured_output
        is False
    )
    assert (
        catalogue.profile("anthropic", "claude-sonnet-4-5").native_structured_output
        is True
    )
    assert catalogue.profile("openai", "gpt-4o-mini").native_structured_output is True
