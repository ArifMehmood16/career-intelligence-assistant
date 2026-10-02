"""Share a local model's slots across jobs and independently constructed adapters."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from career_assistant.application.providers.cancellable import check_provider_cancelled

_pools: dict[tuple[str, str, str, int], threading.BoundedSemaphore] = {}
_guard = threading.Lock()


def _slots(
    provider_id: str, model_tag: str, operation: str, max_in_flight: int
) -> threading.BoundedSemaphore:
    if max_in_flight < 1:
        raise ValueError("local model concurrency must be positive")
    key = provider_id, model_tag, operation, max_in_flight
    with _guard:
        if key not in _pools:
            _pools[key] = threading.BoundedSemaphore(max_in_flight)
        return _pools[key]


@contextmanager
def local_call_slot(
    provider_id: str, model_tag: str, *, operation: str, max_in_flight: int
) -> Iterator[None]:
    """Completion and tools share a pool; embeddings use their own model pool."""
    check_provider_cancelled()
    slots = _slots(provider_id, model_tag, operation, max_in_flight)
    while not slots.acquire(timeout=0.05):
        check_provider_cancelled()
    try:
        check_provider_cancelled()
        yield
    finally:
        slots.release()
