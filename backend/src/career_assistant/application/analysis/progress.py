"""Track one job's tasks and hand every change to a sink (the job's rows)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime

from career_assistant.domain.progress import (
    JobTask,
    TaskKey,
    TaskState,
    advance,
    enter,
    finish,
    skip,
)

Sink = Callable[[tuple[JobTask, ...]], None]


class TrackedProgress:
    """An AnalysisProgress over the domain transitions.

    The sink may raise — the SQL sink raises JobCancelled once the role or the CV
    has been deleted — so each report is also a point where the analysis stops.
    """

    def __init__(
        self,
        plan: Sequence[JobTask],
        *,
        clock: Callable[[], datetime],
        sink: Sink,
    ) -> None:
        self._tasks = tuple(plan)
        self._clock = clock
        self._sink = sink

    @property
    def tasks(self) -> tuple[JobTask, ...]:
        return self._tasks

    def enter(self, key: TaskKey) -> None:
        self._set(enter(self._tasks, key, at=self._clock()))

    def count(self, key: TaskKey, done: int, total: int) -> None:
        self._set(advance(self._tasks, key, units_done=done, units_total=total))

    def skip(self, key: TaskKey) -> None:
        self._set(skip(self._tasks, key, at=self._clock()))

    def finished_tasks(self) -> tuple[JobTask, ...]:
        """The tasks with the running one finished, for the publishing commit."""
        at = self._clock()
        tasks = self._tasks
        for task in self._tasks:
            if task.state is TaskState.RUNNING:
                tasks = finish(tasks, task.key, at=at)
        return tasks

    def _set(self, tasks: tuple[JobTask, ...]) -> None:
        self._sink(tasks)
        self._tasks = tasks
