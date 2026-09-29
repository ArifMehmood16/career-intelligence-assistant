"""The worker's progress tracker: domain transitions, each one sent to a sink."""

from __future__ import annotations

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
        plan_for(PipelineVersion.V1), clock=clock, sink=sent.append
    )
    progress.enter(TaskKey.SCORE)

    final = progress.finished_tasks()

    assert len(sent) == 1, "the caller writes the final tasks with its own commit"
    assert final[-1].state is TaskState.DONE
    assert final[-1].finished_at == clock.now
