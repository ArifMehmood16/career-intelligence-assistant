"""Analysis progress: the tasks a job runs, how far it is, and the time left.

The worker reports task transitions; the API reads them back. The time left is
arithmetic over this job's own pace and the durations of recent jobs — an
estimate, labelled as one, and never a model output. Nothing here holds document
text.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from statistics import median

from career_assistant.domain.jobs import JobState
from career_assistant.domain.pipeline import PipelineVersion


class TaskKey(StrEnum):
    PREPARE = "prepare"
    READ_ADVERT = "read_advert"
    READ_CV = "read_cv"
    SEARCH = "search"
    JUDGE = "judge"
    RECHECK = "recheck"
    SCORE = "score"


class TaskState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


_PLANS: Mapping[PipelineVersion, tuple[TaskKey, ...]] = {
    PipelineVersion.V2: (
        TaskKey.PREPARE,
        TaskKey.READ_CV,
        TaskKey.READ_ADVERT,
        TaskKey.SEARCH,
        TaskKey.JUDGE,
        TaskKey.RECHECK,
        TaskKey.SCORE,
    ),
}

# Tasks with no model call: without history they are assumed to take no time,
# so they never hold back an estimate.
QUICK_TASKS = frozenset({TaskKey.PREPARE, TaskKey.SCORE})
_SETTLED = frozenset({TaskState.DONE, TaskState.SKIPPED, TaskState.FAILED})


@dataclass(frozen=True, slots=True)
class JobTask:
    key: TaskKey
    state: TaskState = TaskState.PENDING
    units_done: int = 0
    units_total: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    model_calls_done: int = 0
    model_calls_total: int | None = None
    embedding_calls_done: int = 0
    embedding_calls_total: int | None = None


@dataclass(frozen=True, slots=True)
class ProgressSummary:
    tasks_done: int
    tasks_total: int
    current: JobTask | None
    fraction: float


@dataclass(frozen=True, slots=True)
class ProgressView:
    """What a person watching the analysis is shown."""

    tasks: tuple[JobTask, ...]
    tasks_done: int
    tasks_total: int
    fraction: float
    current: TaskKey | None
    elapsed_seconds: float | None
    remaining_seconds: float | None
    queue_position: int | None
    model_calls_done: int
    model_calls_remaining: int
    embedding_calls_done: int
    embedding_calls_remaining: int
    call_estimate_complete: bool


@dataclass(frozen=True, slots=True)
class TaskBaseline:
    """Recent median durations of one task, whole and per counted unit."""

    seconds: float
    seconds_per_unit: float | None = None


@dataclass(frozen=True, slots=True)
class TaskSample:
    key: TaskKey
    seconds: float
    units: int | None


Baselines = Mapping[PipelineVersion, Mapping[TaskKey, TaskBaseline]]


def plan_for(pipeline: PipelineVersion) -> tuple[JobTask, ...]:
    return tuple(JobTask(key) for key in _PLANS[pipeline])


def pipeline_of(tasks: Sequence[JobTask]) -> PipelineVersion | None:
    keys = tuple(task.key for task in tasks)
    return next((p for p, plan in _PLANS.items() if plan == keys), None)


def start(
    tasks: Sequence[JobTask],
    key: TaskKey,
    *,
    at: datetime,
    units_total: int | None = None,
) -> tuple[JobTask, ...]:
    task = _find(tasks, key)
    if task.state is not TaskState.PENDING:
        raise ValueError(f"cannot start task {key} in state {task.state}")
    _check_units(0, units_total)
    return _put(
        tasks,
        replace(task, state=TaskState.RUNNING, started_at=at, units_total=units_total),
    )


def advance(
    tasks: Sequence[JobTask],
    key: TaskKey,
    *,
    units_done: int,
    units_total: int | None = None,
) -> tuple[JobTask, ...]:
    task = _find(tasks, key)
    if task.state is not TaskState.RUNNING:
        raise ValueError(f"cannot advance task {key} in state {task.state}")
    total = task.units_total if units_total is None else units_total
    _check_units(units_done, total)
    return _put(tasks, replace(task, units_done=units_done, units_total=total))


def finish(
    tasks: Sequence[JobTask], key: TaskKey, *, at: datetime
) -> tuple[JobTask, ...]:
    task = _find(tasks, key)
    if task.state is not TaskState.RUNNING:
        raise ValueError(f"cannot finish task {key} in state {task.state}")
    done = task.units_total if task.units_total is not None else task.units_done
    return _put(
        tasks, replace(task, state=TaskState.DONE, units_done=done, finished_at=at)
    )


def skip(
    tasks: Sequence[JobTask], key: TaskKey, *, at: datetime
) -> tuple[JobTask, ...]:
    task = _find(tasks, key)
    if task.state is not TaskState.PENDING:
        raise ValueError(f"cannot skip task {key} in state {task.state}")
    return _put(tasks, replace(task, state=TaskState.SKIPPED, finished_at=at))


def enter(
    tasks: Sequence[JobTask], key: TaskKey, *, at: datetime
) -> tuple[JobTask, ...]:
    """Finish whatever is running, then start `key`."""
    moved = tuple(tasks)
    for task in tasks:
        if task.state is TaskState.RUNNING:
            moved = finish(moved, task.key, at=at)
    return start(moved, key, at=at)


def settle(tasks: Sequence[JobTask], job_state: JobState) -> tuple[JobTask, ...]:
    """A failed job's running task is where it stopped."""
    if job_state is not JobState.FAILED:
        return tuple(tasks)
    return tuple(
        replace(task, state=TaskState.FAILED)
        if task.state is TaskState.RUNNING
        else task
        for task in tasks
    )


def summarise(tasks: Sequence[JobTask]) -> ProgressSummary:
    done = sum(1 for task in tasks if task.state in (TaskState.DONE, TaskState.SKIPPED))
    current = next((t for t in tasks if t.state is TaskState.RUNNING), None)
    share = sum(
        task.units_done / task.units_total
        for task in tasks
        if task.state is TaskState.RUNNING and task.units_total
    )
    total = len(tasks)
    return ProgressSummary(
        tasks_done=done,
        tasks_total=total,
        current=current,
        fraction=(done + share) / total if total else 0.0,
    )


def estimate_remaining(
    tasks: Sequence[JobTask],
    *,
    now: datetime,
    baselines: Mapping[TaskKey, TaskBaseline],
) -> float | None:
    """Seconds left, or None while any unfinished model task has no measure."""
    sequential = 0.0
    parallel_reads: list[float] = []
    for task in tasks:
        left = _task_remaining(task, now, baselines.get(task.key))
        if left is None:
            return None
        if task.key in (TaskKey.READ_CV, TaskKey.READ_ADVERT):
            parallel_reads.append(left)
        else:
            sequential += left
    concurrent_reads = (
        sum(
            task.state is TaskState.RUNNING
            for task in tasks
            if task.key in (TaskKey.READ_CV, TaskKey.READ_ADVERT)
        )
        > 1
    )
    reads = (
        max(parallel_reads, default=0.0) if concurrent_reads else sum(parallel_reads)
    )
    return sequential + reads


def progress_view(
    *,
    state: JobState,
    started_at: datetime | None,
    finished_at: datetime | None,
    tasks: Sequence[JobTask],
    now: datetime,
    baselines: Baselines,
    ahead: Sequence[Sequence[JobTask]] = (),
) -> ProgressView:
    """A job's progress. `ahead` is the tasks of each live job before a queued one."""
    settled = settle(tasks, state)
    summary = summarise(settled)
    return ProgressView(
        tasks=settled,
        tasks_done=summary.tasks_done,
        tasks_total=summary.tasks_total,
        fraction=summary.fraction,
        current=summary.current.key if summary.current is not None else None,
        elapsed_seconds=_elapsed(started_at, finished_at, now),
        remaining_seconds=_job_remaining(state, settled, now, baselines, ahead),
        queue_position=len(ahead) if state is JobState.QUEUED else None,
        model_calls_done=sum(t.model_calls_done for t in settled),
        model_calls_remaining=_calls_remaining(settled, "model")
        if state in (JobState.QUEUED, JobState.RUNNING)
        else 0,
        embedding_calls_done=sum(t.embedding_calls_done for t in settled),
        embedding_calls_remaining=_calls_remaining(settled, "embedding")
        if state in (JobState.QUEUED, JobState.RUNNING)
        else 0,
        call_estimate_complete=all(
            t.state in _SETTLED
            or t.key in QUICK_TASKS
            or (t.model_calls_total is not None and t.embedding_calls_total is not None)
            for t in settled
        ),
    )


def baselines_from(samples: Iterable[TaskSample]) -> dict[TaskKey, TaskBaseline]:
    seconds: dict[TaskKey, list[float]] = defaultdict(list)
    per_unit: dict[TaskKey, list[float]] = defaultdict(list)
    for sample in samples:
        seconds[sample.key].append(sample.seconds)
        if sample.units:
            per_unit[sample.key].append(sample.seconds / sample.units)
    return {
        key: TaskBaseline(
            seconds=median(values),
            seconds_per_unit=median(per_unit[key]) if per_unit[key] else None,
        )
        for key, values in seconds.items()
    }


def _elapsed(
    started_at: datetime | None, finished_at: datetime | None, now: datetime
) -> float | None:
    if started_at is None:
        return None
    return max(0.0, ((finished_at or now) - started_at).total_seconds())


def _job_remaining(
    state: JobState,
    tasks: Sequence[JobTask],
    now: datetime,
    baselines: Baselines,
    ahead: Sequence[Sequence[JobTask]],
) -> float | None:
    if state is JobState.SUCCEEDED:
        return 0.0
    if state is JobState.FAILED:
        return None
    waiting = ahead if state is JobState.QUEUED else ()
    total = 0.0
    for job_tasks in (*waiting, tasks):
        pipeline = pipeline_of(job_tasks)
        known = baselines.get(pipeline, {}) if pipeline is not None else {}
        left = estimate_remaining(job_tasks, now=now, baselines=known)
        if left is None:
            return None
        total += left
    return total


def _task_remaining(
    task: JobTask, now: datetime, baseline: TaskBaseline | None
) -> float | None:
    if task.state in _SETTLED:
        return 0.0
    if task.state is TaskState.PENDING or task.started_at is None:
        return _expected(task, baseline)
    elapsed = max(0.0, (now - task.started_at).total_seconds())
    if task.units_total is not None and task.units_done > 0:
        return elapsed / task.units_done * (task.units_total - task.units_done)
    expected = _expected(task, baseline)
    return None if expected is None else max(0.0, expected - elapsed)


def _expected(task: JobTask, baseline: TaskBaseline | None) -> float | None:
    if task.model_calls_total == 0 and task.embedding_calls_total == 0:
        return 0.0
    if baseline is None:
        return 0.0 if task.key in QUICK_TASKS else None
    if task.units_total is not None and baseline.seconds_per_unit is not None:
        return baseline.seconds_per_unit * task.units_total
    return baseline.seconds


def _find(tasks: Sequence[JobTask], key: TaskKey) -> JobTask:
    for task in tasks:
        if task.key is key:
            return task
    raise ValueError(f"task {key} is not in this job's plan")


def _put(tasks: Sequence[JobTask], changed: JobTask) -> tuple[JobTask, ...]:
    return tuple(changed if task.key is changed.key else task for task in tasks)


def _check_units(done: int, total: int | None) -> None:
    if done < 0 or (total is not None and not 0 <= done <= total):
        raise ValueError(f"units done {done} is outside 0..{total}")


def plan_calls(
    tasks: Sequence[JobTask], key: TaskKey, *, model: int = 0, embedding: int = 0
) -> tuple[JobTask, ...]:
    """Add planned requests; discoveries and repairs can extend this estimate."""
    if model < 0 or embedding < 0:
        raise ValueError("planned calls cannot be negative")
    task = _find(tasks, key)
    return _put(
        tasks,
        replace(
            task,
            model_calls_total=(task.model_calls_total or task.model_calls_done) + model,
            embedding_calls_total=(
                task.embedding_calls_total or task.embedding_calls_done
            )
            + embedding,
        ),
    )


def call_finished(
    tasks: Sequence[JobTask], key: TaskKey, *, operation: str
) -> tuple[JobTask, ...]:
    """Count a physical attempt, including a failed attempt."""
    task = _find(tasks, key)
    if operation == "model":
        done = task.model_calls_done + 1
        changed = replace(
            task,
            model_calls_done=done,
            model_calls_total=max(done, task.model_calls_total or 0),
        )
    elif operation == "embedding":
        done = task.embedding_calls_done + 1
        changed = replace(
            task,
            embedding_calls_done=done,
            embedding_calls_total=max(done, task.embedding_calls_total or 0),
        )
    else:
        raise ValueError("unknown call operation")
    return _put(tasks, changed)


def _calls_remaining(tasks: Sequence[JobTask], operation: str) -> int:
    return sum(
        max(0, (t.model_calls_total or 0) - t.model_calls_done)
        if operation == "model"
        else max(0, (t.embedding_calls_total or 0) - t.embedding_calls_done)
        for t in tasks
        if t.state not in _SETTLED
    )
