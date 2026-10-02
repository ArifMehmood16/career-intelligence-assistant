"""Physical attempts, repairs and scoped progress are safe across provider retries."""

from __future__ import annotations

from datetime import UTC, datetime

from career_assistant.adapters.providers.hermetic.completion import (
    HermeticCompletionAdapter,
)
from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.adapters.providers.resilience import ResiliencePolicy
from career_assistant.application.analysis.progress import TrackedProgress
from career_assistant.application.ports.errors import ProviderTransientError
from career_assistant.application.ports.progress import plan_calls, progress_scope
from career_assistant.application.ports.types import (
    CompletionRequest,
    CompletionResult,
    EmbeddingRequest,
)
from career_assistant.application.providers.accounting import (
    AccountingCompletion,
    AccountingEmbedding,
    CallAccountant,
)
from career_assistant.domain.pipeline import PipelineVersion
from career_assistant.domain.progress import TaskKey, plan_for


class _RetryingCompletion(HermeticCompletionAdapter):
    def __init__(self) -> None:
        self.attempts = 0

    def complete(self, request: CompletionRequest) -> CompletionResult:
        def operation() -> CompletionResult:
            self.attempts += 1
            if self.attempts == 1:
                raise ProviderTransientError("upstream status 503")
            return super(_RetryingCompletion, self).complete(request)

        return ResiliencePolicy(1, 1, sleep=lambda _: None).run(operation)


def _progress() -> TrackedProgress:
    return TrackedProgress(
        plan_for(PipelineVersion.V2),
        clock=lambda: datetime.now(UTC),
        sink=lambda _: None,
    )


def test_provider_retry_adds_a_plan_and_counts_both_attempts() -> None:
    progress = _progress()
    accountant = CallAccountant()
    completion = AccountingCompletion(
        _RetryingCompletion(), accountant, workspace_id="ws", purpose="judge"
    )
    with progress_scope(progress, TaskKey.JUDGE):
        plan_calls(model=1)
        completion.complete(
            CompletionRequest(system="", user="hello", max_output_tokens=50)
        )
    judge = next(t for t in progress.tasks if t.key is TaskKey.JUDGE)
    assert (judge.model_calls_done, judge.model_calls_total) == (2, 2)
    assert len(accountant.records) == 1


def test_scoped_completion_and_embedding_remain_separate() -> None:
    progress = _progress()
    accountant = CallAccountant()
    completion = AccountingCompletion(
        HermeticCompletionAdapter(), accountant, workspace_id="ws", purpose="read"
    )
    embedding = AccountingEmbedding(
        HermeticEmbeddingAdapter(), accountant, workspace_id="ws", purpose="index"
    )
    with progress_scope(progress, TaskKey.READ_CV):
        plan_calls(model=1, embedding=1)
        completion.complete(
            CompletionRequest(system="", user="hello", max_output_tokens=50)
        )
        embedding.embed(
            EmbeddingRequest(texts=("hello", "world"), max_chars_per_text=100)
        )
    cv = next(t for t in progress.tasks if t.key is TaskKey.READ_CV)
    assert (cv.model_calls_done, cv.embedding_calls_done) == (1, 1)
    plan_calls(model=99)
    assert progress.tasks[1] == cv
