"""The worker's progress tracker: domain transitions, each one sent to a sink."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta

from career_assistant.application.analysis.progress import TrackedProgress
from career_assistant.domain.pipeline import PipelineVersion
from career_assistant.domain.progress import JobTask, TaskKey, TaskState, plan_for

T0 = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


class _Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


def _states(tasks: tuple[JobTask, ...]) -> list[str]:
    return [f"{t.key.value}:{t.state.value}" for t in tasks]


def test_each_change_is_sent_to_the_sink_in_order() -> None:
    sent: list[tuple[JobTask, ...]] = []
    progress = TrackedProgress(
        plan_for(PipelineVersion.V2), clock=_Clock(), sink=sent.append
    )

    progress.enter(TaskKey.PREPARE)
    progress.enter(TaskKey.READ_CV)
    progress.count(TaskKey.READ_CV, 1, 2)
    progress.skip(TaskKey.RECHECK)

    assert len(sent) == 4
    assert _states(sent[1])[:2] == ["prepare:done", "read_cv:running"]
    last = sent[-1]
    assert (last[1].units_done, last[1].units_total) == (1, 2)
    assert last[5].state is TaskState.SKIPPED
    assert progress.tasks == last


def test_the_final_tasks_finish_the_running_one_without_sending() -> None:
    sent: list[tuple[JobTask, ...]] = []
    clock = _Clock()
    progress = TrackedProgress(
        plan_for(PipelineVersion.V2), clock=clock, sink=sent.append
    )
    progress.enter(TaskKey.SCORE)

    final = progress.finished_tasks()

    assert len(sent) == 1, "the caller writes the final tasks with its own commit"
    assert final[-1].state is TaskState.DONE
    assert final[-1].finished_at == clock.now


def test_overlapping_counts_reach_the_sink_one_at_a_time() -> None:
    gate = threading.Lock()
    seen: list[int] = []

    def sink(tasks: tuple[JobTask, ...]) -> None:
        assert gate.acquire(blocking=False)
        try:
            time.sleep(0.01)
            judge = next(task for task in tasks if task.key is TaskKey.JUDGE)
            seen.append(judge.units_done)
        finally:
            gate.release()

    progress = TrackedProgress(plan_for(PipelineVersion.V2), clock=_Clock(), sink=sink)
    progress.enter(TaskKey.JUDGE)
    threads = [
        threading.Thread(target=progress.count, args=(TaskKey.JUDGE, done, 4))
        for done in (1, 2, 3, 4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(seen) == [0, 1, 2, 3, 4]


def test_independent_starts_and_finishes_keep_other_stage_running() -> None:
    progress = TrackedProgress(
        plan_for(PipelineVersion.V2), clock=_Clock(), sink=lambda _: None
    )
    progress.start(TaskKey.READ_CV)
    progress.start(TaskKey.READ_ADVERT)
    progress.finish(TaskKey.READ_CV)
    states = {task.key: task.state for task in progress.tasks}
    assert states[TaskKey.READ_CV] is TaskState.DONE
    assert states[TaskKey.READ_ADVERT] is TaskState.RUNNING


def test_concurrent_physical_call_counts_are_not_lost() -> None:
    progress = TrackedProgress(
        plan_for(PipelineVersion.V2), clock=_Clock(), sink=lambda _: None
    )
    progress.plan_calls(TaskKey.JUDGE, model=20)
    threads = [
        threading.Thread(
            target=progress.call_finished,
            args=(TaskKey.JUDGE,),
            kwargs={"operation": "model"},
        )
        for _ in range(20)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    judge = next(task for task in progress.tasks if task.key is TaskKey.JUDGE)
    assert (judge.model_calls_done, judge.model_calls_total) == (20, 20)
