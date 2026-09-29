"""Embeddings know whether they embed a query or a document (PLAN 18.1).

nomic-embed-text was trained with task prefixes; without them it runs outside the
mode it was trained for. The prefixes are model configuration, so the adapter
never branches on a model's name. A request with no input type is a v1 request
and is embedded exactly as before.
"""

from __future__ import annotations

import pytest
from tests.support.recording_transport import RecordingTransport

from career_assistant.adapters.providers.ollama.embedding import OllamaEmbeddingAdapter
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
)
from career_assistant.application.ports.types import EmbeddingRequest, ModelProfile

_NOMIC = ModelProfile(
    context_window_tokens=2_048,
    max_output_tokens=0,
    embedding_query_prefix="search_query: ",
    embedding_document_prefix="search_document: ",
)


def _adapter(
    transport: RecordingTransport, profile: ModelProfile = _NOMIC
) -> OllamaEmbeddingAdapter:
    return OllamaEmbeddingAdapter(
        base_url="http://ollama.test",
        model_tag="nomic-embed-text",
        transport=transport,
        resilience=ResiliencePolicy(
            timeout_seconds=1.0,
            max_retries=0,
            breaker=CircuitBreaker(5),
            sleep=lambda _seconds: None,
        ),
        dimensions=3,
        profile=profile,
    )


def _embed(
    transport: RecordingTransport,
    input_type: str | None,
    profile: ModelProfile = _NOMIC,
) -> None:
    _adapter(transport, profile).embed(
        EmbeddingRequest(
            texts=("Built hybrid retrieval.",),
            max_chars_per_text=1_000,
            input_type=input_type,  # type: ignore[arg-type]
        )
    )


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        ("query", "search_query: Built hybrid retrieval."),
        ("document", "search_document: Built hybrid retrieval."),
        (None, "Built hybrid retrieval."),
    ],
)
def test_the_configured_prefix_is_applied_for_the_input_type(
    input_type: str | None, expected: str
) -> None:
    transport = RecordingTransport({"embedding": [0.1, 0.2, 0.3]})

    _embed(transport, input_type)

    assert transport.last.body["prompt"] == expected


def test_a_model_with_no_prefixes_is_embedded_unchanged() -> None:
    transport = RecordingTransport({"embedding": [0.1, 0.2, 0.3]})

    _embed(
        transport,
        "query",
        ModelProfile(context_window_tokens=8_192, max_output_tokens=0),
    )

    assert transport.last.body["prompt"] == "Built hybrid retrieval."


def test_the_embedding_context_window_is_sent_explicitly() -> None:
    transport = RecordingTransport({"embedding": [0.1, 0.2, 0.3]})

    _embed(transport, "document")

    assert transport.last.body["options"] == {"num_ctx": 2_048}
