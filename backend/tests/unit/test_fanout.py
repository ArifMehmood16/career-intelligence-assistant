"""Independent I/O overlaps without unbounded threads or lost accounting context."""

import threading
from contextvars import ContextVar

from career_assistant.application.providers.fanout import map_in_order


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
        2, 4, 6, 8
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
