"""How an analysis reports its progress (the worker and the pipelines)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Protocol

from career_assistant.domain.progress import TaskKey


class AnalysisProgress(Protocol):
    def start(self, key: TaskKey) -> None: ...

    def finish(self, key: TaskKey) -> None: ...

    def enter(self, key: TaskKey) -> None:
        """Finish the running task, if any, and start `key`."""
        ...

    def count(self, key: TaskKey, done: int, total: int) -> None: ...

    def skip(self, key: TaskKey) -> None: ...

    def plan_calls(
        self, key: TaskKey, *, model: int = 0, embedding: int = 0
    ) -> None: ...

    def call_finished(self, key: TaskKey, *, operation: str) -> None: ...


class NoProgress:
    """For callers with nobody watching: tests and the in-memory path."""

    def enter(self, key: TaskKey) -> None:
        del key

    def start(self, key: TaskKey) -> None:
        del key

    def finish(self, key: TaskKey) -> None:
        del key

    def count(self, key: TaskKey, done: int, total: int) -> None:
        del key, done, total

    def skip(self, key: TaskKey) -> None:
        del key

    def plan_calls(self, key: TaskKey, *, model: int = 0, embedding: int = 0) -> None:
        del key, model, embedding

    def call_finished(self, key: TaskKey, *, operation: str) -> None:
        del key, operation


NO_PROGRESS = NoProgress()


@dataclass(frozen=True)
class _Scope:
    progress: AnalysisProgress
    key: TaskKey


_scope: ContextVar[_Scope | None] = ContextVar("analysis_progress_scope", default=None)


@contextmanager
def progress_scope(progress: AnalysisProgress, key: TaskKey) -> Iterator[None]:
    """Attribute nested calls to a task; callers copy the context into threads."""
    token = _scope.set(_Scope(progress, key))
    try:
        yield
    finally:
        _scope.reset(token)


def plan_calls(*, model: int = 0, embedding: int = 0) -> None:
    scope = _scope.get()
    if scope is not None:
        scope.progress.plan_calls(scope.key, model=model, embedding=embedding)


def record_call(operation: str) -> None:
    scope = _scope.get()
    if scope is not None:
        scope.progress.call_finished(scope.key, operation=operation)
