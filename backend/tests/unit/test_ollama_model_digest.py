"""Ollama reports the digest of the weights behind a tag (ADR 014, PLAN 18.7).

A local tag can be re-pulled to different weights, so the verdict cache keys on
the digest. A lookup that fails reports none, which only costs a cache miss.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from tests.support.scripted_transport import ScriptedTransport

from career_assistant.adapters.providers.factory import build_completion_port
from career_assistant.adapters.providers.http_transport import HttpResponse
from career_assistant.adapters.providers.ollama.completion import (
    OllamaCompletionAdapter,
)
from career_assistant.adapters.providers.ollama.digest import ollama_model_digest
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
)
from career_assistant.application.ports.errors import ProviderUnavailableError
from career_assistant.settings import ProviderSettings

TAGS = {
    "models": [
        {"name": "nomic-embed-text:latest", "digest": "sha256:embed"},
        {"name": "qwen2.5:7b", "digest": "sha256:qwen7b"},
        {"name": "llama3.2:latest", "digest": "sha256:llama"},
    ]
}


def _tags(body: object, status: int = 200) -> ScriptedTransport:
    encoded = body if isinstance(body, bytes) else json.dumps(body).encode()
    return ScriptedTransport({"/api/tags": HttpResponse(status, encoded, {})})


def _digest(transport: object, tag: str) -> str | None:
    return ollama_model_digest(
        transport,  # type: ignore[arg-type]
        base_url="http://ollama.test",
        model_tag=tag,
        timeout_seconds=1.0,
    )


@dataclass
class _Unreachable:
    calls: list[str] = field(default_factory=list)

    def request(self, method: str, url: str, **_: object) -> HttpResponse:
        self.calls.append(url)
        raise ProviderUnavailableError("provider could not be reached")


def test_the_digest_of_the_configured_tag_is_reported() -> None:
    transport = _tags(TAGS)

    assert _digest(transport, "qwen2.5:7b") == "sha256:qwen7b"
    assert transport.calls == [("GET", "http://ollama.test/api/tags")]


def test_a_tag_without_a_version_means_latest() -> None:
    assert _digest(_tags(TAGS), "llama3.2") == "sha256:llama"


def test_a_tag_that_is_not_pulled_has_no_digest() -> None:
    assert _digest(_tags(TAGS), "qwen2.5:14b") is None


def test_an_error_status_or_a_malformed_body_has_no_digest() -> None:
    assert _digest(_tags(TAGS, status=500), "qwen2.5:7b") is None
    assert _digest(_tags(b"not json"), "qwen2.5:7b") is None
    assert _digest(_tags({"models": "nope"}), "qwen2.5:7b") is None
    assert _digest(_tags({"models": [{"name": "qwen2.5:7b"}]}), "qwen2.5:7b") is None


def test_an_unreachable_server_has_no_digest() -> None:
    assert _digest(_Unreachable(), "qwen2.5:7b") is None


def _adapter(lookup: object = None) -> OllamaCompletionAdapter:
    return OllamaCompletionAdapter(
        base_url="http://ollama.test",
        model_tag="qwen2.5:7b",
        transport=ScriptedTransport({}),
        resilience=ResiliencePolicy(
            timeout_seconds=1.0,
            max_retries=0,
            breaker=CircuitBreaker(5),
            sleep=lambda _seconds: None,
        ),
        digest_lookup=lookup,  # type: ignore[arg-type]
    )


def test_the_adapter_reports_the_digest_and_looks_it_up_once() -> None:
    calls: list[int] = []

    def lookup() -> str | None:
        calls.append(1)
        return "sha256:qwen7b"

    adapter = _adapter(lookup)

    assert adapter.capabilities.model_digest == "sha256:qwen7b"
    assert adapter.capabilities.model_digest == "sha256:qwen7b"
    assert len(calls) == 1


def test_a_failed_lookup_is_tried_again_next_time() -> None:
    replies = [None, "sha256:qwen7b"]
    adapter = _adapter(lambda: replies.pop(0))

    assert adapter.capabilities.model_digest is None
    assert adapter.capabilities.model_digest == "sha256:qwen7b"


def test_an_adapter_without_a_lookup_reports_no_digest() -> None:
    assert _adapter().capabilities.model_digest is None


def test_the_factory_gives_ollama_its_digest_lookup() -> None:
    settings = ProviderSettings(
        _env_file=None,  # type: ignore[call-arg]
        completion_provider="ollama",
        ollama_completion_model="qwen2.5:7b",
        ollama_base_url="http://ollama.test",
    )

    port = build_completion_port(settings, transport=_tags(TAGS))

    assert port.capabilities.model_digest == "sha256:qwen7b"
