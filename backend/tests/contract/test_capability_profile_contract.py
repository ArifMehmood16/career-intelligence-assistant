"""Every HTTP adapter reports the model profile it was built with.

PLAN 18.1: context window, output limit and capability flags come from the model
catalogue, so the application reads one descriptor and never a vendor constant.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from tests.support.scripted_transport import ScriptedTransport

from career_assistant.adapters.providers.anthropic.completion import (
    AnthropicCompletionAdapter,
)
from career_assistant.adapters.providers.hermetic.completion import (
    HermeticCompletionAdapter,
)
from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.adapters.providers.ollama.completion import (
    OllamaCompletionAdapter,
)
from career_assistant.adapters.providers.ollama.embedding import OllamaEmbeddingAdapter
from career_assistant.adapters.providers.openai.completion import (
    OpenAICompletionAdapter,
)
from career_assistant.adapters.providers.openai.embedding import OpenAIEmbeddingAdapter
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
)
from career_assistant.application.ports.types import CapabilityDescriptor, ModelProfile

_PROFILE = ModelProfile(
    context_window_tokens=12_345,
    max_output_tokens=678,
    supports_tool_calling=True,
    supports_prompt_caching=True,
    supports_temperature=True,
    supports_seed=True,
)


def _resilience() -> ResiliencePolicy:
    return ResiliencePolicy(
        timeout_seconds=1.0,
        max_retries=0,
        breaker=CircuitBreaker(5),
        sleep=lambda _seconds: None,
    )


def _http() -> dict[str, object]:
    return {"transport": ScriptedTransport({}), "resilience": _resilience()}


_BUILDERS: dict[str, Callable[[], object]] = {
    "ollama-completion": lambda: OllamaCompletionAdapter(
        base_url="http://ollama.test", model_tag="m", profile=_PROFILE, **_http()
    ),
    "openai-completion": lambda: OpenAICompletionAdapter(
        api_key="k", model_tag="m", profile=_PROFILE, **_http()
    ),
    "anthropic-completion": lambda: AnthropicCompletionAdapter(
        api_key="k", model_tag="m", profile=_PROFILE, **_http()
    ),
    "ollama-embedding": lambda: OllamaEmbeddingAdapter(
        base_url="http://ollama.test", model_tag="m", profile=_PROFILE, **_http()
    ),
    "openai-embedding": lambda: OpenAIEmbeddingAdapter(
        api_key="k", model_tag="m", profile=_PROFILE, **_http()
    ),
}


@pytest.mark.parametrize("name", sorted(_BUILDERS))
def test_capabilities_report_the_injected_model_profile(name: str) -> None:
    caps: CapabilityDescriptor = _BUILDERS[name]().capabilities  # type: ignore[attr-defined]

    assert caps.context_window_tokens == 12_345
    assert caps.supports_tool_calling is True
    assert caps.supports_prompt_caching is True
    assert caps.supports_temperature is True
    assert caps.supports_seed is True


@pytest.mark.parametrize(
    "name", sorted(key for key in _BUILDERS if key.endswith("-completion"))
)
def test_completion_output_limit_comes_from_the_profile(name: str) -> None:
    caps: CapabilityDescriptor = _BUILDERS[name]().capabilities  # type: ignore[attr-defined]

    assert caps.max_output_tokens == 678


@pytest.mark.parametrize(
    "adapter",
    [HermeticCompletionAdapter(), HermeticEmbeddingAdapter()],
    ids=["hermetic-completion", "hermetic-embedding"],
)
def test_the_hermetic_fixture_claims_no_optional_capability(adapter: object) -> None:
    caps: CapabilityDescriptor = adapter.capabilities  # type: ignore[attr-defined]

    assert caps.supports_tool_calling is False
    assert caps.supports_prompt_caching is False
    assert caps.supports_temperature is False
    assert caps.supports_seed is False
