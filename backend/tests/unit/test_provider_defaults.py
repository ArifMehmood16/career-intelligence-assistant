"""PLAN 13C.1 — a real model is the default; hermetic is a test fixture.

The hermetic adapters exist so `make test` runs with no key, no network and no
model download. They were also the shipped default, so a real user's extraction
was done by a bullet regex and a twelve-keyword competency list. Nothing in a
user-facing configuration file selects them any more.
"""

from __future__ import annotations

from pathlib import Path

from career_assistant.main import create_app
from career_assistant.settings import ProviderSettings

ROOT = Path(__file__).resolve().parents[3]
APP_ENV_EXAMPLE = ROOT / "config" / "app.env.example"
BACKEND_SRC = ROOT / "backend" / "src"


def test_provider_defaults_are_a_local_model_not_the_test_fixture() -> None:
    settings = ProviderSettings(_env_file=None)

    assert settings.completion_provider == "ollama"
    assert settings.embedding_provider == "ollama"


def test_the_test_app_factory_still_builds_a_hermetic_app() -> None:
    """`make test` must stay offline whatever the shipped default becomes."""
    app = create_app()

    assert app.state.providers.completion_provider == "hermetic"
    assert app.state.providers.embedding_provider == "hermetic"


def test_the_shipped_configuration_example_selects_a_local_model() -> None:
    text = APP_ENV_EXAMPLE.read_text(encoding="utf-8")

    assert "COMPLETION_PROVIDER=ollama" in text
    assert "EMBEDDING_PROVIDER=ollama" in text
    assert "COMPLETION_PROVIDER=hermetic" not in text
    assert "EMBEDDING_PROVIDER=hermetic" not in text


def test_no_dead_extraction_strategy_switch_remains() -> None:
    """The key was configured and read nowhere. Routing is by provider id."""
    assert "EXTRACTION_STRATEGY" not in APP_ENV_EXAMPLE.read_text(encoding="utf-8")

    offenders = [
        path.relative_to(ROOT)
        for path in BACKEND_SRC.rglob("*.py")
        if "EXTRACTION_STRATEGY" in path.read_text(encoding="utf-8")
        or "extraction_strategy" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"dead extraction-strategy switch referenced in {offenders}"
