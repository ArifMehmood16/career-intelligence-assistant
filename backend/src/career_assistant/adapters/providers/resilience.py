"""Timeout, bounded retry and circuit breaker around HTTP provider calls."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TypeVar

from career_assistant.adapters.providers.call_gate import (
    RETRY_AFTER_CAP_SECONDS,
    retry_after_seconds,
)
from career_assistant.application.ports.errors import (
    ProviderTransientError,
    ProviderUnavailableError,
)
from career_assistant.application.providers.accounting import provider_attempt

T = TypeVar("T")
_BACKOFF_CAP_SECONDS = 1.0
_BACKOFF_BASE_SECONDS = 0.05


@dataclass
class CircuitBreaker:
    failure_threshold: int
    _failures: int = 0
    _open: bool = False
    _guard: threading.Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._guard = threading.Lock()

    def before_call(self) -> None:
        with self._guard:
            if self._open:
                raise ProviderUnavailableError("provider circuit breaker is open")

    def record_success(self) -> None:
        with self._guard:
            self._failures = 0
            self._open = False

    def record_failure(self) -> None:
        with self._guard:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._open = True


@dataclass
class ResiliencePolicy:
    timeout_seconds: float
    max_retries: int
    breaker: CircuitBreaker = field(default_factory=lambda: CircuitBreaker(5))
    sleep: Callable[[float], None] = time.sleep

    def run(self, operation: Callable[[], T]) -> T:
        self.breaker.before_call()
        attempt = 0
        while True:
            try:
                with provider_attempt(retry=attempt > 0):
                    result = operation()
                self.breaker.record_success()
                return result
            except ProviderTransientError as exc:
                self.breaker.record_failure()
                if not _should_retry(exc, attempt, self.max_retries):
                    raise
                self.sleep(_retry_delay(exc, attempt))
                attempt += 1
            except Exception:
                self.breaker.record_failure()
                raise


def classify_http_status(
    status_code: int, headers: Mapping[str, str] | None = None
) -> None:
    if status_code == 429:
        raise ProviderTransientError(
            f"upstream status {status_code}",
            retry_after_seconds=retry_after_seconds(headers or {}),
            rate_limited=True,
        )
    if status_code >= 500:
        raise ProviderTransientError(f"upstream status {status_code}")
    if status_code >= 400:
        raise ProviderUnavailableError(f"upstream status {status_code}")


def _should_retry(exc: ProviderTransientError, attempt: int, max_retries: int) -> bool:
    # A 429 with no Retry-After will not succeed by trying again immediately.
    if exc.rate_limited and exc.retry_after_seconds is None:
        return False
    return attempt < max_retries


def _retry_delay(exc: ProviderTransientError, attempt: int) -> float:
    if exc.rate_limited and exc.retry_after_seconds is not None:
        return min(exc.retry_after_seconds, RETRY_AFTER_CAP_SECONDS)
    delay = _BACKOFF_BASE_SECONDS
    for _ in range(attempt):
        delay *= 2
    return min(delay, _BACKOFF_CAP_SECONDS)
