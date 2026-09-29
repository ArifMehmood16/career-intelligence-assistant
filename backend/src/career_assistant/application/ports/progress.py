"""How an analysis reports its progress (the worker and the pipelines)."""

from __future__ import annotations

from typing import Protocol

from career_assistant.domain.progress import TaskKey


class AnalysisProgress(Protocol):
    def enter(self, key: TaskKey) -> None:
        """Finish the running task, if any, and start `key`."""
        ...

    def count(self, key: TaskKey, done: int, total: int) -> None: ...

    def skip(self, key: TaskKey) -> None: ...


class NoProgress:
    """For callers with nobody watching: tests and the in-memory path."""

    def enter(self, key: TaskKey) -> None:
        del key

    def count(self, key: TaskKey, done: int, total: int) -> None:
        del key, done, total

    def skip(self, key: TaskKey) -> None:
        del key


NO_PROGRESS = NoProgress()
