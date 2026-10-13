"""Track one job's tasks and hand every change to a sink (the job's rows)."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from datetime import datetime

from career_assistant.domain.progress import (
    JobTask,
    TaskKey,
    TaskState,
    advance,
    call_finished,
    enter,
    finish,
    plan_calls,
    skip,
    start,
)
from career_assistant.logconfig import log_event

_log = logging.getLogger(__name__)
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
        self._lock = threading.Lock()

    @property
    def tasks(self) -> tuple[JobTask, ...]:
        with self._lock:
            return self._tasks

    def start(self, key: TaskKey) -> None:
        with self._lock:
            self._set(start(self._tasks, key, at=self._clock()))

    def finish(self, key: TaskKey) -> None:
        with self._lock:
            self._set(finish(self._tasks, key, at=self._clock()))

    def enter(self, key: TaskKey) -> None:
        with self._lock:
            self._set(enter(self._tasks, key, at=self._clock()))

    def count(self, key: TaskKey, done: int, total: int) -> None:
        with self._lock:
            self._set(advance(self._tasks, key, units_done=done, units_total=total))

    def skip(self, key: TaskKey) -> None:
        with self._lock:
            self._set(skip(self._tasks, key, at=self._clock()))

    def plan_calls(self, key: TaskKey, *, model: int = 0, embedding: int = 0) -> None:
        with self._lock:
            self._set(plan_calls(self._tasks, key, model=model, embedding=embedding))

    def call_finished(self, key: TaskKey, *, operation: str) -> None:
        with self._lock:
            self._set(call_finished(self._tasks, key, operation=operation))

    def finished_tasks(self) -> tuple[JobTask, ...]:
        """The tasks with the running one finished, for the publishing commit."""
        with self._lock:
            at = self._clock()
            tasks = self._tasks
            for task in self._tasks:
                if task.state is TaskState.RUNNING:
                    tasks = finish(tasks, task.key, at=at)
            return tasks

    def _set(self, tasks: tuple[JobTask, ...]) -> None:
        self._sink(tasks)
        before = {task.key: task.state for task in self._tasks}
        self._tasks = tasks
        for task in tasks:
            if before.get(task.key) is not task.state:
                _log_transition(task)


def _log_transition(task: JobTask) -> None:
    if task.state is TaskState.RUNNING:
        log_event(_log, "Task started", task=task.key.value)
    elif task.state is TaskState.DONE:
        log_event(
            _log,
            "Task finished",
            task=task.key.value,
            duration_ms=_duration_ms(task),
            units=f"{task.units_done}/{task.units_total}"
            if task.units_total is not None
            else None,
            model_calls=task.model_calls_done or None,
            embedding_calls=task.embedding_calls_done or None,
        )
    elif task.state is TaskState.SKIPPED:
        log_event(_log, "Task skipped", task=task.key.value)


def _duration_ms(task: JobTask) -> int | None:
    if task.started_at is None or task.finished_at is None:
        return None
    return int((task.finished_at - task.started_at).total_seconds() * 1000)
