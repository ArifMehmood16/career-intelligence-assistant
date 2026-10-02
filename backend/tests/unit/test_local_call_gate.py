"""Local model limits apply across independent jobs and port instances."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from career_assistant.adapters.providers.local_gate import local_call_slot
from career_assistant.application.providers.cancellable import cancellation_scope


def test_same_model_and_operation_share_slots_across_threads() -> None:
    entered = threading.Event()
    started = threading.Event()

    def pending() -> None:
        started.set()
        with local_call_slot(
            "ollama", "shared-model", operation="completion", max_in_flight=1
        ):
            entered.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with local_call_slot(
            "ollama", "shared-model", operation="completion", max_in_flight=1
        ):
            future = pool.submit(pending)
            assert started.wait(timeout=1)
            assert not entered.wait(timeout=0.1)
        future.result(timeout=1)
    assert entered.is_set()


def test_configured_two_slots_allow_parallel_calls() -> None:
    barrier = threading.Barrier(2, timeout=1)

    def one() -> None:
        with local_call_slot(
            "ollama", "parallel-model", operation="completion", max_in_flight=2
        ):
            barrier.wait()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(one) for _ in range(2)]
        for future in futures:
            future.result(timeout=2)


def test_embedding_and_completion_have_independent_model_slots() -> None:
    with local_call_slot(
        "ollama", "different-operations", operation="completion", max_in_flight=1
    ):
        with local_call_slot(
            "ollama", "different-operations", operation="embedding", max_in_flight=1
        ):
            pass


def test_cancelled_waiter_does_not_start_a_provider_call() -> None:
    started = threading.Event()
    cancelled = threading.Event()

    class Cancelled(Exception):
        pass

    def check() -> None:
        started.set()
        if cancelled.is_set():
            raise Cancelled

    def pending() -> None:
        with cancellation_scope(check):
            with local_call_slot(
                "ollama", "cancel-model", operation="completion", max_in_flight=1
            ):
                raise AssertionError("cancelled provider call started")

    with ThreadPoolExecutor(max_workers=1) as pool:
        with local_call_slot(
            "ollama", "cancel-model", operation="completion", max_in_flight=1
        ):
            future = pool.submit(pending)
            assert started.wait(timeout=1)
            cancelled.set()
            with pytest.raises(Cancelled):
                future.result(timeout=1)
        with local_call_slot(
            "ollama", "cancel-model", operation="completion", max_in_flight=1
        ):
            pass
