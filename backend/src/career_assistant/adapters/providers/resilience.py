"""Timeout, bounded retry and circuit breaker around HTTP provider calls."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar

from career_assistant.application.ports.errors import (
    ProviderTransientError,
    ProviderUnavailableError,
)

T = TypeVar("T")


@dataclass
class CircuitBreaker:
    failure_threshold: int
    _failures: int = 0
    _open: bool = False

    def before_call(self) -> None:
        if self._open:
            raise ProviderUnavailableError("provider circuit breaker is open")

    def record_success(self) -> None:
        self._failures = 0
        self._open = False

    def record_failure(self) -> None:
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
                result = operation()
                self.breaker.record_success()
                return result
            except ProviderTransientError:
                self.breaker.record_failure()
                if attempt >= self.max_retries:
                    raise
                self.sleep(min(2**attempt * 0.05, 1.0))
                attempt += 1
            except Exception:
                self.breaker.record_failure()
                raise


def classify_http_status(status_code: int) -> None:
    if status_code == 429 or status_code >= 500:
        raise ProviderTransientError(f"upstream status {status_code}")
    if status_code >= 400:
        raise ProviderUnavailableError(f"upstream status {status_code}")
