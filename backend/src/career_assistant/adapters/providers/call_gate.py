"""Keep hosted model calls inside the allowance the last response reported.

One gate is shared by completion and embedding. It caps how many hosted calls
are in flight, and it will not start another call for a model whose latest
rate-limit headers cannot cover the estimate. Local calls never enter it:
callers pass None when the capability descriptor says nothing leaves the machine.
The gate does not name a vendor. It reads whichever remaining-request and
remaining-token headers the response carried.
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from career_assistant.application.providers.cancellable import check_provider_cancelled


class _Retrying(Protocol):
    def run[R](self, operation: Callable[[], R]) -> R: ...


RETRY_AFTER_CAP_SECONDS = 60.0
_RESERVATION_POLL_SECONDS = 0.01
_CHARS_PER_TOKEN = 4
_DURATION = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?(?:(\d+)ms)?$")

_OPENAI_REMAINING_REQUESTS = "x-ratelimit-remaining-requests"
_OPENAI_REMAINING_TOKENS = "x-ratelimit-remaining-tokens"
_OPENAI_RESET_REQUESTS = "x-ratelimit-reset-requests"
_OPENAI_RESET_TOKENS = "x-ratelimit-reset-tokens"
_ANTHROPIC_REMAINING_REQUESTS = "anthropic-ratelimit-requests-remaining"
_ANTHROPIC_RESET_REQUESTS = "anthropic-ratelimit-requests-reset"
_ANTHROPIC_REMAINING_INPUT = "anthropic-ratelimit-input-tokens-remaining"
_ANTHROPIC_RESET_INPUT = "anthropic-ratelimit-input-tokens-reset"
_ANTHROPIC_REMAINING_OUTPUT = "anthropic-ratelimit-output-tokens-remaining"
_ANTHROPIC_RESET_OUTPUT = "anthropic-ratelimit-output-tokens-reset"
_RETRY_AFTER = "retry-after"
_RETRY_AFTER_MS = "retry-after-ms"


class RateLimitNote(Protocol):
    def __call__(
        self, headers: Mapping[str, str], *, used_tokens: int | None = None
    ) -> None: ...


def ignore_rate_limit(
    headers: Mapping[str, str], *, used_tokens: int | None = None
) -> None:
    del headers, used_tokens


def estimate_tokens(char_count: int, max_output_tokens: int = 0) -> int:
    """Rough reservation: four characters a token, plus the output cap."""
    return max(1, char_count // _CHARS_PER_TOKEN + max_output_tokens)


def retry_after_seconds(headers: Mapping[str, str]) -> float | None:
    """The vendor wait, capped, or None when the 429 did not include one."""
    millis = _header(headers, _RETRY_AFTER_MS)
    if millis is not None:
        parsed = _positive_float(millis)
        if parsed is not None:
            return min(parsed / 1000.0, RETRY_AFTER_CAP_SECONDS)
    raw = _header(headers, _RETRY_AFTER)
    if raw is None:
        return None
    parsed = _positive_float(raw)
    if parsed is None:
        return None
    return min(parsed, RETRY_AFTER_CAP_SECONDS)


@dataclass
class _Budget:
    remaining_requests: int | None = None
    remaining_tokens: int | None = None
    requests_ready_at: float = 0.0
    tokens_ready_at: float = 0.0
    reserved_requests: int = 0
    reserved_tokens: int = 0


@dataclass
class HostedCallGate:
    """Process-wide burst cap and per-model token window for hosted calls."""

    max_in_flight: int = 4
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    wall_clock: Callable[[], float] = time.time
    _slots: threading.Semaphore = field(init=False, repr=False)
    _guard: threading.Lock = field(init=False, repr=False)
    _budgets: dict[tuple[str, str], _Budget] = field(init=False, repr=False)
    _in_flight: int = field(init=False, default=0, repr=False)
    _peak: int = field(init=False, default=0, repr=False)

    def __post_init__(self) -> None:
        if self.max_in_flight < 1:
            raise ValueError("max_in_flight must be at least 1")
        self._slots = threading.Semaphore(self.max_in_flight)
        self._guard = threading.Lock()
        self._budgets = {}

    @property
    def in_flight(self) -> int:
        with self._guard:
            return self._in_flight

    @property
    def peak_in_flight(self) -> int:
        with self._guard:
            return self._peak

    def run[T](
        self,
        *,
        provider_id: str,
        model_tag: str,
        estimated_tokens: int,
        operation: Callable[[RateLimitNote], T],
    ) -> T:
        estimate = max(1, estimated_tokens)
        key = (provider_id, model_tag)
        check_provider_cancelled()
        self._await_budget(key, estimate)
        acquired = False
        marked = False
        try:
            while not self._slots.acquire(timeout=0.05):
                check_provider_cancelled()
            acquired = True
            check_provider_cancelled()
            self._mark(1)
            marked = True
            return operation(
                lambda headers, used_tokens=None: self.observe(
                    provider_id, model_tag, headers, used_tokens=used_tokens
                )
            )
        finally:
            self._release(key, estimate)
            if marked:
                self._mark(-1)
            if acquired:
                self._slots.release()

    def observe(
        self,
        provider_id: str,
        model_tag: str,
        headers: Mapping[str, str],
        *,
        used_tokens: int | None = None,
    ) -> None:
        """Store the remaining allowance from this response."""
        # The headers already count this call, so they replace the estimate.
        del used_tokens
        requests, request_reset = _requests(headers)
        tokens, token_reset = _tokens(headers)
        with self._guard:
            budget = self._budgets.setdefault((provider_id, model_tag), _Budget())
            if requests is not None:
                budget.remaining_requests = requests
                budget.requests_ready_at = self._ready(request_reset)
            if tokens is not None:
                budget.remaining_tokens = tokens
                budget.tokens_ready_at = self._ready(token_reset)

    def _await_budget(self, key: tuple[str, str], estimate: int) -> None:
        while True:
            check_provider_cancelled()
            with self._guard:
                budget = self._budgets.setdefault(key, _Budget())
                _expire(budget, estimate, now=self.clock())
                if _fits(budget, estimate):
                    budget.reserved_requests += 1
                    budget.reserved_tokens += estimate
                    return
                delay = _delay(budget, estimate, now=self.clock())
            self.sleep(min(delay, 1.0))

    def _release(self, key: tuple[str, str], estimate: int) -> None:
        with self._guard:
            budget = self._budgets[key]
            budget.reserved_requests = max(0, budget.reserved_requests - 1)
            budget.reserved_tokens = max(0, budget.reserved_tokens - estimate)

    def _mark(self, delta: int) -> None:
        with self._guard:
            self._in_flight += delta
            self._peak = max(self._peak, self._in_flight)

    def _ready(self, raw: str | None) -> float:
        now = self.clock()
        if raw is None:
            return now
        wait = min(
            _seconds_until(raw, wall_now=self.wall_clock()), RETRY_AFTER_CAP_SECONDS
        )
        return now + wait


def run_hosted[T](
    gate: HostedCallGate | None,
    *,
    provider_id: str,
    model_tag: str,
    estimated_tokens: int,
    resilience: _Retrying,
    operation: Callable[[RateLimitNote], T],
) -> T:
    """Run one hosted call through the gate, or straight through when there is none."""
    if gate is None:
        return resilience.run(lambda: operation(ignore_rate_limit))
    return gate.run(
        provider_id=provider_id,
        model_tag=model_tag,
        estimated_tokens=estimated_tokens,
        operation=lambda note: resilience.run(lambda: operation(note)),
    )


_shared: HostedCallGate | None = None
_shared_guard = threading.Lock()


def shared_hosted_call_gate(max_in_flight: int) -> HostedCallGate:
    """The one gate for this process. The first caller sets the burst cap."""
    global _shared
    with _shared_guard:
        if _shared is None:
            _shared = HostedCallGate(max_in_flight=max_in_flight)
        return _shared


def _fits(budget: _Budget, estimate: int) -> bool:
    if budget.remaining_requests is not None:
        if budget.remaining_requests - budget.reserved_requests < 1:
            return False
    if budget.remaining_tokens is not None:
        if budget.remaining_tokens - budget.reserved_tokens < estimate:
            return False
    return True


def _expire(budget: _Budget, estimate: int, *, now: float) -> None:
    """A window whose reset has passed is unknown again, so the next call may go."""
    requests_short = (
        budget.remaining_requests is not None
        and budget.remaining_requests - budget.reserved_requests < 1
    )
    if requests_short and budget.requests_ready_at <= now:
        budget.remaining_requests = None
    tokens_short = (
        budget.remaining_tokens is not None
        and budget.remaining_tokens - budget.reserved_tokens < estimate
    )
    if tokens_short and budget.tokens_ready_at <= now:
        budget.remaining_tokens = None


def _delay(budget: _Budget, estimate: int, *, now: float) -> float:
    delay = 0.0
    if budget.remaining_requests is not None and budget.remaining_requests < 1:
        delay = max(delay, budget.requests_ready_at - now)
    if budget.remaining_tokens is not None and budget.remaining_tokens < estimate:
        delay = max(delay, budget.tokens_ready_at - now)
    if delay > 0:
        return min(delay, RETRY_AFTER_CAP_SECONDS)
    return _RESERVATION_POLL_SECONDS


def _requests(headers: Mapping[str, str]) -> tuple[int | None, str | None]:
    remaining = _int_header(headers, _OPENAI_REMAINING_REQUESTS)
    reset = _header(headers, _OPENAI_RESET_REQUESTS)
    if remaining is None:
        remaining = _int_header(headers, _ANTHROPIC_REMAINING_REQUESTS)
        reset = _header(headers, _ANTHROPIC_RESET_REQUESTS)
    return remaining, reset


def _tokens(headers: Mapping[str, str]) -> tuple[int | None, str | None]:
    """The tightest token bucket the response reported, and when it refills."""
    windows = (
        (_OPENAI_REMAINING_TOKENS, _OPENAI_RESET_TOKENS),
        (_ANTHROPIC_REMAINING_INPUT, _ANTHROPIC_RESET_INPUT),
        (_ANTHROPIC_REMAINING_OUTPUT, _ANTHROPIC_RESET_OUTPUT),
    )
    found: list[tuple[int, str | None]] = []
    for remaining_name, reset_name in windows:
        remaining = _int_header(headers, remaining_name)
        if remaining is not None:
            found.append((remaining, _header(headers, reset_name)))
    if not found:
        return None, None
    return min(found, key=lambda item: item[0])


def _header(headers: Mapping[str, str], name: str) -> str | None:
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted and value.strip():
            return value.strip()
    return None


def _int_header(headers: Mapping[str, str], name: str) -> int | None:
    raw = _header(headers, name)
    if raw is None:
        return None
    try:
        return int(raw.replace(",", ""))
    except ValueError:
        return None


def _positive_float(raw: str) -> float | None:
    try:
        value = float(raw)
    except ValueError:
        return None
    if value < 0:
        return None
    return value


def _seconds_until(raw: str, *, wall_now: float) -> float:
    if "T" in raw:
        try:
            moment = datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
        return max(0.0, moment - wall_now)
    duration = _duration_seconds(raw)
    if duration is None:
        return 0.0
    return duration


def _duration_seconds(raw: str) -> float | None:
    match = _DURATION.fullmatch(raw.strip())
    if match is None:
        return None
    hours, minutes, seconds, millis = match.groups()
    if hours is minutes is seconds is millis is None:
        return None
    total = 0.0
    if hours is not None:
        total += int(hours) * 3600
    if minutes is not None:
        total += int(minutes) * 60
    if seconds is not None:
        total += float(seconds)
    if millis is not None:
        total += int(millis) / 1000.0
    return total
