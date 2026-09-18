"""Embedding contract — hermetic plus recorded HTTP adapters."""

from __future__ import annotations

import json

import pytest
from tests.support.scripted_transport import ScriptedTransport

from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.adapters.providers.http_transport import HttpResponse
from career_assistant.adapters.providers.ollama.embedding import OllamaEmbeddingAdapter
from career_assistant.adapters.providers.openai.embedding import OpenAIEmbeddingAdapter
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
)
from career_assistant.application.ports.errors import ProviderInputTooLargeError
from career_assistant.application.ports.types import EmbeddingRequest


def _resilience() -> ResiliencePolicy:
    return ResiliencePolicy(
        timeout_seconds=1.0,
        max_retries=0,
        breaker=CircuitBreaker(5),
        sleep=lambda _seconds: None,
    )


@pytest.fixture(
    params=[
        pytest.param(lambda: HermeticEmbeddingAdapter(), id="hermetic"),
        pytest.param(
            lambda: OllamaEmbeddingAdapter(
                base_url="http://ollama.test",
                model_tag="nomic-test",
                transport=ScriptedTransport(
                    {
                        "/api/embeddings": HttpResponse(
                            200,
                            json.dumps({"embedding": [0.1, 0.2, 0.3]}).encode(),
                            {},
                        )
                    }
                ),
                resilience=_resilience(),
                dimensions=3,
            ),
            id="ollama",
        ),
        pytest.param(
            lambda: OpenAIEmbeddingAdapter(
                api_key="test-key",
                model_tag="emb-test",
                transport=ScriptedTransport(
                    {
                        "/embeddings": HttpResponse(
                            200,
                            json.dumps(
                                {
                                    "data": [
                                        {"embedding": [0.5, 0.25, 0.125]},
                                        {"embedding": [0.1, 0.2, 0.3]},
                                    ],
                                    "usage": {"total_tokens": 2},
                                }
                            ).encode(),
                            {},
                        )
                    }
                ),
                resilience=_resilience(),
                dimensions=3,
            ),
            id="openai",
        ),
    ]
)
def embedder(request: pytest.FixtureRequest) -> object:
    return request.param()


def test_embed_returns_one_vector_per_text(embedder: object) -> None:
    result = embedder.embed(  # type: ignore[attr-defined]
        EmbeddingRequest(texts=("alpha", "beta"), max_chars_per_text=1000)
    )
    assert len(result.vectors) == 2
    assert result.dimensions == len(result.vectors[0])
    assert all(len(vector) == result.dimensions for vector in result.vectors)


def test_hermetic_embeddings_are_stable() -> None:
    adapter = HermeticEmbeddingAdapter()
    request = EmbeddingRequest(texts=("dbt snowflake",), max_chars_per_text=1000)
    assert adapter.embed(request).vectors == adapter.embed(request).vectors


def test_oversized_embedding_input_rejected() -> None:
    adapter = HermeticEmbeddingAdapter()
    with pytest.raises(ProviderInputTooLargeError):
        adapter.embed(EmbeddingRequest(texts=("x" * 50,), max_chars_per_text=10))
