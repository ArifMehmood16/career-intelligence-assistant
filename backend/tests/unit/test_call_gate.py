"""Hosted calls share a burst cap and honour the rate-limit headers."""

from __future__ import annotations

import threading
import time
from datetime import datetime

import pytest

from career_assistant.adapters.providers.call_gate import HostedCallGate, RateLimitNote
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
    classify_http_status,
)
from career_assistant.application.ports.errors import (
    ProviderTransientError,
    ProviderUnavailableError,
)
from career_assistant.application.ports.types import CallRecord
from career_assistant.application.providers.accounting import CallAccountant


def _clock(now: list[float]) -> tuple[HostedCallGate, list[float]]:
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    gate = HostedCallGate(
        max_in_flight=4, sleep=sleep, clock=lambda: now[0], wall_clock=lambda: 0.0
    )
    return gate, slept


def test_in_flight_never_exceeds_the_ceiling() -> None:
    gate = HostedCallGate(max_in_flight=2)
    hold = threading.Event()

    def operation(note: RateLimitNote) -> None:
        del note
        hold.wait(timeout=2)

    threads = [
        threading.Thread(
            target=lambda: gate.run(
                provider_id="openai",
                model_tag="gpt-4o-mini",
                estimated_tokens=10,
                operation=operation,
            )
        )
        for _ in range(4)
    ]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and gate.in_flight < 2:
        time.sleep(0.01)
    assert gate.in_flight == 2
    time.sleep(0.05)
    assert gate.in_flight == 2
    assert gate.peak_in_flight == 2
    hold.set()
    for thread in threads:
        thread.join(timeout=2)
        assert not thread.is_alive()


def test_a_call_waits_until_the_token_window_resets() -> None:
    now = [0.0]
    gate, slept = _clock(now)

    def first(note: RateLimitNote) -> str:
        note(
            {
                "x-ratelimit-remaining-requests": "9",
                "x-ratelimit-reset-requests": "1s",
                "x-ratelimit-remaining-tokens": "50",
                "x-ratelimit-reset-tokens": "5s",
            }
        )
        return "a"

    assert (
        gate.run(
            provider_id="openai",
            model_tag="gpt-4o-mini",
            estimated_tokens=80,
            operation=first,
        )
        == "a"
    )
    assert (
        gate.run(
            provider_id="openai",
            model_tag="gpt-4o-mini",
            estimated_tokens=80,
            operation=lambda note: "b",
        )
        == "b"
    )
    assert sum(slept) == 5.0
    assert all(0 < delay <= 1.0 for delay in slept)


def test_a_long_reset_is_capped() -> None:
    now = [0.0]
    gate, slept = _clock(now)
    gate.observe(
        "openai",
        "gpt-4o",
        {
            "x-ratelimit-remaining-requests": "10",
            "x-ratelimit-reset-requests": "1s",
            "x-ratelimit-remaining-tokens": "0",
            "x-ratelimit-reset-tokens": "120s",
        },
    )

    gate.run(
        provider_id="openai",
        model_tag="gpt-4o",
        estimated_tokens=10,
        operation=lambda note: None,
    )

    assert sum(slept) == 60.0
    assert all(0 < delay <= 1.0 for delay in slept)


def test_one_vendors_window_does_not_block_another() -> None:
    now = [0.0]
    gate, slept = _clock(now)
    gate.observe(
        "openai",
        "gpt-4o-mini",
        {
            "x-ratelimit-remaining-requests": "0",
            "x-ratelimit-reset-requests": "30s",
            "x-ratelimit-remaining-tokens": "0",
            "x-ratelimit-reset-tokens": "30s",
        },
    )

    gate.run(
        provider_id="anthropic",
        model_tag="claude-sonnet-4-5",
        estimated_tokens=1_000,
        operation=lambda note: None,
    )

    assert slept == []


def test_anthropic_uses_the_tighter_token_bucket() -> None:
    now = [0.0]
    slept: list[float] = []
    wall = datetime.fromisoformat("2026-09-29T00:00:00+00:00").timestamp()

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    gate = HostedCallGate(
        max_in_flight=4,
        sleep=sleep,
        clock=lambda: now[0],
        wall_clock=lambda: wall,
    )
    gate.observe(
        "anthropic",
        "claude-sonnet-4-5",
        {
            "anthropic-ratelimit-requests-remaining": "100",
            "anthropic-ratelimit-requests-reset": "2026-09-29T00:00:30Z",
            "anthropic-ratelimit-input-tokens-remaining": "2000000",
            "anthropic-ratelimit-input-tokens-reset": "2026-09-29T00:00:30Z",
            "anthropic-ratelimit-output-tokens-remaining": "10",
            "anthropic-ratelimit-output-tokens-reset": "2026-09-29T00:00:04Z",
        },
    )

    gate.run(
        provider_id="anthropic",
        model_tag="claude-sonnet-4-5",
        estimated_tokens=100,
        operation=lambda note: None,
    )

    assert sum(slept) == 4.0
    assert all(0 < delay <= 1.0 for delay in slept)


def test_rate_limit_without_retry_after_is_not_retried() -> None:
    calls = {"n": 0}

    def fail() -> None:
        calls["n"] += 1
        raise ProviderTransientError("upstream status 429", rate_limited=True)

    policy = ResiliencePolicy(
        timeout_seconds=1.0,
        max_retries=2,
        breaker=CircuitBreaker(5),
        sleep=lambda _seconds: None,
    )
    with pytest.raises(ProviderTransientError):
        policy.run(fail)
    assert calls["n"] == 1


def test_rate_limit_waits_for_retry_after_and_caps_it() -> None:
    slept: list[float] = []
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ProviderTransientError(
                "upstream status 429", rate_limited=True, retry_after_seconds=90
            )
        return "ok"

    policy = ResiliencePolicy(
        timeout_seconds=1.0,
        max_retries=2,
        breaker=CircuitBreaker(5),
        sleep=slept.append,
    )
    assert policy.run(flaky) == "ok"
    assert slept == [60.0]


def test_classify_keeps_retry_after_and_ignores_a_missing_one() -> None:
    with pytest.raises(ProviderTransientError) as limited:
        classify_http_status(429, {"retry-after-ms": "1500"})
    assert limited.value.rate_limited is True
    assert limited.value.retry_after_seconds == 1.5

    with pytest.raises(ProviderTransientError) as bare:
        classify_http_status(429)
    assert bare.value.retry_after_seconds is None

    with pytest.raises(ProviderTransientError) as server:
        classify_http_status(503)
    assert server.value.rate_limited is False


def test_a_closed_breaker_is_still_unavailable() -> None:
    breaker = CircuitBreaker(failure_threshold=1)
    policy = ResiliencePolicy(
        timeout_seconds=1.0, max_retries=0, breaker=breaker, sleep=lambda _s: None
    )

    def fail() -> str:
        raise ProviderTransientError("upstream status 500")

    with pytest.raises(ProviderTransientError):
        policy.run(fail)
    with pytest.raises(ProviderUnavailableError):
        policy.run(lambda: "ok")


def test_concurrent_accounting_keeps_every_record() -> None:
    accountant = CallAccountant()

    def record(index: int) -> None:
        accountant.record(
            CallRecord(
                provider_id="openai",
                model_tag="gpt-4o-mini",
                operation="complete",
                input_tokens=index,
                output_tokens=1,
                latency_ms=1,
                estimated_cost_usd=None,
                left_machine=True,
            )
        )

    threads = [threading.Thread(target=record, args=(index,)) for index in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(accountant.records) == 20
