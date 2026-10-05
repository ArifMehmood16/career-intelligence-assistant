"""A cancelled analysis starts no further provider calls (roles or CV deleted)."""

from __future__ import annotations

import pytest
from tests.support.scripted_completion import Reply, ScriptedCompletion

from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.application.contracts.chunking import JobChunkResponse
from career_assistant.application.ports.errors import JobCancelled
from career_assistant.application.ports.structured import StructuredRequest
from career_assistant.application.ports.types import (
    CompletionRequest,
    EmbeddingRequest,
)
from career_assistant.application.providers.cancellable import (
    CancellableCompletion,
    CancellableEmbedding,
    CancellableStructured,
)


class _Switch:
    def __init__(self) -> None:
        self.cancelled = False
        self.checks = 0

    def __call__(self) -> None:
        self.checks += 1
        if self.cancelled:
            raise JobCancelled("job-1")


def _completion_request() -> CompletionRequest:
    return CompletionRequest(system="s", user="u", max_output_tokens=10)


def test_a_completion_is_checked_before_each_call_and_stops_once_cancelled() -> None:
    inner = ScriptedCompletion([Reply("one"), Reply("two")])
    switch = _Switch()
    port = CancellableCompletion(inner, switch)

    assert port.complete(_completion_request()).text == "one"
    switch.cancelled = True
    with pytest.raises(JobCancelled):
        port.complete(_completion_request())

    assert len(inner.requests) == 1
    assert switch.checks == 3
    assert port.capabilities == inner.capabilities


def test_a_structured_call_is_not_sent_once_cancelled() -> None:
    inner = HermeticStructuredCompleter()
    switch = _Switch()
    port = CancellableStructured(inner, switch)
    request = StructuredRequest(
        contract=JobChunkResponse,
        system="s",
        user="<document>\nL1: Requirements\nL2: - Python\n</document>",
        max_output_tokens=100,
    )

    assert port.complete_structured(request).value.chunks
    switch.cancelled = True
    with pytest.raises(JobCancelled):
        port.complete_structured(request)
    assert port.capabilities == inner.capabilities


def test_an_embedding_call_is_not_sent_once_cancelled() -> None:
    inner = HermeticEmbeddingAdapter()
    switch = _Switch()
    port = CancellableEmbedding(inner, switch)
    request = EmbeddingRequest(texts=("python",), max_chars_per_text=100)

    assert len(port.embed(request).vectors) == 1
    switch.cancelled = True
    with pytest.raises(JobCancelled):
        port.embed(request)
    assert port.capabilities == inner.capabilities


def test_a_response_is_discarded_if_the_job_is_cancelled_during_the_call() -> None:
    switch = _Switch()

    class CancellingCompletion(ScriptedCompletion):
        def complete(self, request: CompletionRequest):
            result = super().complete(request)
            switch.cancelled = True
            return result

    inner = CancellingCompletion([Reply("late response")])
    with pytest.raises(JobCancelled):
        CancellableCompletion(inner, switch).complete(_completion_request())
    assert len(inner.requests) == 1
