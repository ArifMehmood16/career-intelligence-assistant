"""Run independent calls together and return them in input order.

The injected model profile bounds concurrency. Context follows each call so
progress, cancellation and audit attribution survive a thread boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context


def map_in_order[T, R](
    items: Sequence[T],
    function: Callable[[T], R],
    *,
    parallel: bool,
    max_workers: int = 4,
) -> list[R]:
    if max_workers < 1:
        raise ValueError("max_workers must be positive")
    if not parallel or len(items) < 2 or max_workers == 1:
        return [function(item) for item in items]
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as pool:
        futures = [pool.submit(copy_context().run, function, item) for item in items]
        try:
            return [future.result() for future in futures]
        except BaseException:
            for future in futures:
                future.cancel()
            raise
