"""Independent I/O overlaps without unbounded threads or lost accounting context."""

import threading
from contextvars import ContextVar
from datetime import UTC, datetime

from career_assistant.adapters.providers.hermetic.completion import (
    HermeticCompletionAdapter,
)
from career_assistant.adapters.providers.resilience import ResiliencePolicy
from career_assistant.application.analysis.progress import TrackedProgress
from career_assistant.application.ports.errors import ProviderTransientError
from career_assistant.application.ports.progress import plan_calls, progress_scope
from career_assistant.application.ports.types import CompletionRequest, CompletionResult
from career_assistant.application.providers.accounting import (
    AccountingCompletion,
    CallAccountant,
)
from career_assistant.application.providers.cancellable import cancellation_scope
from career_assistant.application.providers.fanout import map_in_order
from career_assistant.domain.pipeline import PipelineVersion
from career_assistant.domain.progress import TaskKey, plan_for


def test_parallel_fanout_bounds_threads_and_preserves_input_order() -> None:
    barrier = threading.Barrier(2)
    lock = threading.Lock()
    active = peak = 0

    def work(item: int) -> int:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        barrier.wait(timeout=2)
        with lock:
            active -= 1
        return item * 2

    assert map_in_order((1, 2, 3, 4), work, parallel=True, max_workers=2) == [
        2,
        4,
        6,
        8,
    ]
    assert peak == 2


def test_parallel_fanout_copies_the_call_accounting_context_for_each_task() -> None:
    current_job: ContextVar[str] = ContextVar("current_job", default="missing")
    token = current_job.set("job-123")
    try:
        result = map_in_order(
            (1, 2), lambda _: current_job.get(), parallel=True, max_workers=2
        )
    finally:
        current_job.reset(token)
    assert result == ["job-123", "job-123"]


def test_one_worker_uses_the_calling_thread() -> None:
    calling_thread = threading.get_ident()
    assert map_in_order(
        (1, 2), lambda _: threading.get_ident(), parallel=True, max_workers=1
    ) == [calling_thread, calling_thread]


class ParallelRetryCompletion(HermeticCompletionAdapter):
    def __init__(self, barrier: threading.Barrier, *, retry: bool) -> None:
        self.attempts = 0
        self._barrier = barrier
        self._retry = retry

    def complete(self, request: CompletionRequest) -> CompletionResult:
        def operation() -> CompletionResult:
            self.attempts += 1
            if self.attempts == 1:
                self._barrier.wait(timeout=2)
                if self._retry:
                    raise ProviderTransientError("synthetic upstream 503")
            return super(ParallelRetryCompletion, self).complete(request)

        return ResiliencePolicy(1, 1, sleep=lambda _: None).run(operation)


def test_parallel_provider_retries_keep_actual_task_and_cancellation_scopes() -> None:
    progress = TrackedProgress(
        plan_for(PipelineVersion.V2),
        clock=lambda: datetime.now(UTC),
        sink=lambda _: None,
    )
    accountant = CallAccountant()
    barrier = threading.Barrier(2)
    checked_threads: set[int] = set()
    lock = threading.Lock()

    def check() -> None:
        with lock:
            checked_threads.add(threading.get_ident())

    def call(retry: bool) -> CompletionResult:
        completion = AccountingCompletion(
            ParallelRetryCompletion(barrier, retry=retry),
            accountant,
            workspace_id="synthetic-ws",
            purpose="judge",
        )
        return completion.complete(
            CompletionRequest(system="", user="synthetic", max_output_tokens=50)
        )

    with cancellation_scope(check), progress_scope(progress, TaskKey.JUDGE):
        plan_calls(model=2)
        replies = map_in_order((False, True), call, parallel=True, max_workers=2)

    assert len(replies) == 2
    judge = next(task for task in progress.tasks if task.key is TaskKey.JUDGE)
    assert (judge.model_calls_done, judge.model_calls_total) == (3, 3)
    assert len(accountant.records) == 2
    assert len(checked_threads) == 2
    assert threading.get_ident() not in checked_threads


def test_cancelled_parent_scope_prevents_dispatch_and_adds_no_attempts() -> None:
    progress = TrackedProgress(
        plan_for(PipelineVersion.V2),
        clock=lambda: datetime.now(UTC),
        sink=lambda _: None,
    )
    accountant = CallAccountant()
    inner = ParallelRetryCompletion(threading.Barrier(2), retry=False)
    completion = AccountingCompletion(
        inner, accountant, workspace_id="synthetic-ws", purpose="judge"
    )

    class Cancelled(Exception):
        pass

    def cancelled() -> None:
        raise Cancelled

    def call(_: int) -> bool:
        try:
            completion.complete(
                CompletionRequest(system="", user="synthetic", max_output_tokens=50)
            )
        except Cancelled:
            return True
        return False

    with cancellation_scope(cancelled), progress_scope(progress, TaskKey.JUDGE):
        plan_calls(model=2)
        assert map_in_order((1, 2), call, parallel=True, max_workers=2) == [True, True]
    judge = next(task for task in progress.tasks if task.key is TaskKey.JUDGE)
    assert (judge.model_calls_done, judge.model_calls_total) == (0, 2)
    assert inner.attempts == 0
    assert accountant.records == ()
