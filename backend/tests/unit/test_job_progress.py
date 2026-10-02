"""Analysis progress: task plans, transitions and the time-left estimate (pure)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from career_assistant.domain.jobs import JobState
from career_assistant.domain.pipeline import PipelineVersion
from career_assistant.domain.progress import (
    JobTask,
    TaskBaseline,
    TaskKey,
    TaskSample,
    TaskState,
    advance,
    baselines_from,
    call_finished,
    enter,
    estimate_remaining,
    finish,
    pipeline_of,
    plan_calls,
    plan_for,
    progress_view,
    settle,
    skip,
    start,
    summarise,
)

T0 = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def _at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def _task(tasks: tuple[JobTask, ...], key: TaskKey) -> JobTask:
    return next(task for task in tasks if task.key is key)


def _running(pipeline: PipelineVersion, key: TaskKey) -> tuple[JobTask, ...]:
    """Every task before `key` finished at T0, and `key` running since T0."""
    tasks = plan_for(pipeline)
    for planned in plan_for(pipeline):
        tasks = enter(tasks, planned.key, at=T0)
        if planned.key is key:
            return tasks
    raise AssertionError(key)


def test_each_pipeline_plans_its_tasks_in_run_order() -> None:
    assert [t.key for t in plan_for(PipelineVersion.V2)] == [
        TaskKey.PREPARE,
        TaskKey.READ_CV,
        TaskKey.READ_ADVERT,
        TaskKey.SEARCH,
        TaskKey.JUDGE,
        TaskKey.RECHECK,
        TaskKey.SCORE,
    ]
    assert all(t.state is TaskState.PENDING for t in plan_for(PipelineVersion.V2))


def test_a_task_starts_counts_units_and_finishes() -> None:
    tasks = start(plan_for(PipelineVersion.V2), TaskKey.JUDGE, at=_at(1))
    tasks = advance(tasks, TaskKey.JUDGE, units_done=0, units_total=12)
    tasks = advance(tasks, TaskKey.JUDGE, units_done=4)
    judge = _task(tasks, TaskKey.JUDGE)
    assert (judge.state, judge.units_done, judge.units_total) == (
        TaskState.RUNNING,
        4,
        12,
    )
    assert judge.started_at == _at(1)

    done = _task(finish(tasks, TaskKey.JUDGE, at=_at(9)), TaskKey.JUDGE)
    assert (done.state, done.units_done, done.finished_at) == (
        TaskState.DONE,
        12,
        _at(9),
    )


def test_enter_finishes_the_running_task_and_starts_the_next() -> None:
    tasks = enter(plan_for(PipelineVersion.V2), TaskKey.PREPARE, at=_at(0))
    tasks = enter(tasks, TaskKey.READ_ADVERT, at=_at(2))
    assert _task(tasks, TaskKey.PREPARE).state is TaskState.DONE
    assert _task(tasks, TaskKey.PREPARE).finished_at == _at(2)
    assert _task(tasks, TaskKey.READ_ADVERT).state is TaskState.RUNNING


def test_a_task_with_nothing_to_do_is_skipped() -> None:
    tasks = skip(plan_for(PipelineVersion.V2), TaskKey.RECHECK, at=_at(5))
    recheck = _task(tasks, TaskKey.RECHECK)
    assert (recheck.state, recheck.started_at, recheck.finished_at) == (
        TaskState.SKIPPED,
        None,
        _at(5),
    )


@pytest.mark.parametrize(
    "change",
    [
        lambda t: finish(t, TaskKey.SCORE, at=_at(1)),
        lambda t: advance(t, TaskKey.SCORE, units_done=1),
        lambda t: start(start(t, TaskKey.SCORE, at=_at(1)), TaskKey.SCORE, at=_at(2)),
    ],
)
def test_illegal_transitions_are_rejected(
    change: Callable[[tuple[JobTask, ...]], object],
) -> None:
    with pytest.raises(ValueError):
        change(plan_for(PipelineVersion.V2))


def test_units_cannot_exceed_the_total() -> None:
    tasks = start(plan_for(PipelineVersion.V2), TaskKey.JUDGE, at=_at(0))
    with pytest.raises(ValueError):
        advance(tasks, TaskKey.JUDGE, units_done=5, units_total=4)


def test_summary_counts_done_and_skipped_and_the_running_share() -> None:
    tasks = _running(PipelineVersion.V2, TaskKey.JUDGE)
    tasks = advance(tasks, TaskKey.JUDGE, units_done=3, units_total=12)

    summary = summarise(tasks)

    assert (summary.tasks_done, summary.tasks_total) == (4, 7)
    assert summary.current is not None
    assert summary.current.key is TaskKey.JUDGE
    assert summary.fraction == pytest.approx((4 + 3 / 12) / 7)


def test_a_failed_job_shows_where_it_stopped() -> None:
    tasks = enter(plan_for(PipelineVersion.V2), TaskKey.READ_ADVERT, at=_at(0))

    settled = settle(tasks, JobState.FAILED)

    assert _task(settled, TaskKey.READ_ADVERT).state is TaskState.FAILED
    assert _task(settled, TaskKey.READ_CV).state is TaskState.PENDING
    assert settle(tasks, JobState.RUNNING) == tasks


def test_time_left_uses_this_jobs_own_pace_inside_a_counted_task() -> None:
    tasks = _running(PipelineVersion.V2, TaskKey.JUDGE)
    tasks = advance(tasks, TaskKey.JUDGE, units_done=4, units_total=12)
    tasks = skip(tasks, TaskKey.RECHECK, at=_at(0))

    # 4 requirements in 20 s -> 8 left at 5 s each; the score task is quick.
    assert estimate_remaining(tasks, now=_at(20), baselines={}) == pytest.approx(40)


def test_time_left_uses_recent_durations_for_tasks_not_yet_measured() -> None:
    tasks = enter(plan_for(PipelineVersion.V2), TaskKey.READ_ADVERT, at=_at(0))
    baselines = {
        TaskKey.READ_ADVERT: TaskBaseline(seconds=30),
        TaskKey.READ_CV: TaskBaseline(seconds=50),
        TaskKey.SEARCH: TaskBaseline(seconds=20),
        TaskKey.JUDGE: TaskBaseline(seconds=0),
        TaskKey.RECHECK: TaskBaseline(seconds=0),
    }

    # Before concurrent starts are observed, the estimate remains conservative.
    assert estimate_remaining(tasks, now=_at(10), baselines=baselines) == 90


def test_a_task_past_its_usual_duration_counts_as_almost_done() -> None:
    tasks = _running(PipelineVersion.V2, TaskKey.SEARCH)
    baselines = {
        TaskKey.SEARCH: TaskBaseline(seconds=5),
        TaskKey.JUDGE: TaskBaseline(seconds=0),
        TaskKey.RECHECK: TaskBaseline(seconds=0),
    }

    assert estimate_remaining(tasks, now=_at(60), baselines=baselines) == 0


def test_a_counted_task_uses_the_recent_pace_per_unit_before_its_first_unit() -> None:
    tasks = _running(PipelineVersion.V2, TaskKey.JUDGE)
    tasks = advance(tasks, TaskKey.JUDGE, units_done=0, units_total=10)
    tasks = skip(tasks, TaskKey.RECHECK, at=_at(0))
    baselines = {TaskKey.JUDGE: TaskBaseline(seconds=99, seconds_per_unit=3)}

    assert estimate_remaining(tasks, now=_at(6), baselines=baselines) == 24


def test_time_left_is_unknown_while_any_model_task_has_no_measure() -> None:
    tasks = enter(plan_for(PipelineVersion.V2), TaskKey.READ_CV, at=_at(0))

    assert estimate_remaining(tasks, now=_at(5), baselines={}) is None


def test_finished_tasks_add_no_time() -> None:
    tasks = _running(PipelineVersion.V2, TaskKey.SCORE)
    tasks = finish(tasks, TaskKey.SCORE, at=_at(2))

    assert estimate_remaining(tasks, now=_at(3), baselines={}) == 0


def test_baselines_are_medians_of_recent_tasks() -> None:
    samples = [
        TaskSample(TaskKey.READ_CV, seconds=10, units=None),
        TaskSample(TaskKey.READ_CV, seconds=40, units=None),
        TaskSample(TaskKey.READ_CV, seconds=30, units=None),
        TaskSample(TaskKey.JUDGE, seconds=20, units=10),
        TaskSample(TaskKey.JUDGE, seconds=12, units=4),
        TaskSample(TaskKey.JUDGE, seconds=0, units=0),
    ]

    baselines = baselines_from(samples)

    assert baselines[TaskKey.READ_CV] == TaskBaseline(seconds=30)
    assert baselines[TaskKey.JUDGE] == TaskBaseline(seconds=12, seconds_per_unit=2.5)


_BASELINES = {
    PipelineVersion.V2: {
        TaskKey.READ_ADVERT: TaskBaseline(seconds=30),
        TaskKey.READ_CV: TaskBaseline(seconds=50),
        TaskKey.SEARCH: TaskBaseline(seconds=20),
        TaskKey.JUDGE: TaskBaseline(seconds=0),
        TaskKey.RECHECK: TaskBaseline(seconds=0),
    }
}


def test_a_running_jobs_view_counts_times_and_names_the_current_task() -> None:
    tasks = _running(PipelineVersion.V2, TaskKey.READ_CV)

    view = progress_view(
        state=JobState.RUNNING,
        started_at=T0,
        finished_at=None,
        tasks=tasks,
        now=_at(15),
        baselines=_BASELINES,
    )

    assert (view.tasks_done, view.tasks_total) == (1, 7)
    assert view.current is TaskKey.READ_CV
    assert view.elapsed_seconds == 15
    assert view.remaining_seconds == 50 - 15 + 30 + 20
    assert view.queue_position is None


def test_a_failed_jobs_view_marks_where_it_stopped_and_has_no_time_left() -> None:
    tasks = _running(PipelineVersion.V2, TaskKey.SEARCH)

    view = progress_view(
        state=JobState.FAILED,
        started_at=T0,
        finished_at=_at(40),
        tasks=tasks,
        now=_at(99),
        baselines=_BASELINES,
    )

    assert view.tasks[3].state is TaskState.FAILED
    assert view.current is None
    assert view.elapsed_seconds == 40
    assert view.remaining_seconds is None


def test_a_succeeded_jobs_view_has_nothing_left() -> None:
    view = progress_view(
        state=JobState.SUCCEEDED,
        started_at=T0,
        finished_at=_at(70),
        tasks=finish(
            _running(PipelineVersion.V2, TaskKey.SCORE), TaskKey.SCORE, at=_at(70)
        ),
        now=_at(99),
        baselines={},
    )

    assert (view.tasks_done, view.remaining_seconds) == (7, 0)


def test_a_queued_job_waits_for_the_jobs_ahead_then_its_own_tasks() -> None:
    ahead_running = _running(PipelineVersion.V2, TaskKey.SEARCH)  # 20 s, 10 gone
    ahead_queued = plan_for(PipelineVersion.V2)  # 100 s

    view = progress_view(
        state=JobState.QUEUED,
        started_at=None,
        finished_at=None,
        tasks=plan_for(PipelineVersion.V2),
        now=_at(10),
        baselines=_BASELINES,
        ahead=(ahead_running, ahead_queued),
    )

    assert view.queue_position == 2
    assert view.elapsed_seconds is None
    assert view.remaining_seconds == 10 + 100 + 100


def test_a_queued_jobs_time_is_unknown_when_any_job_ahead_is() -> None:
    view = progress_view(
        state=JobState.QUEUED,
        started_at=None,
        finished_at=None,
        tasks=plan_for(PipelineVersion.V2),
        now=_at(10),
        baselines={},
        ahead=(_running(PipelineVersion.V2, TaskKey.JUDGE),),
    )

    assert view.remaining_seconds is None


def test_the_pipeline_is_read_from_the_task_plan() -> None:
    assert pipeline_of(plan_for(PipelineVersion.V2)) is PipelineVersion.V2
    assert pipeline_of(_running(PipelineVersion.V2, TaskKey.SEARCH)) is (
        PipelineVersion.V2
    )
    assert pipeline_of(()) is None


def test_parallel_read_tasks_both_count_toward_progress() -> None:
    tasks = start(plan_for(PipelineVersion.V2), TaskKey.READ_CV, at=T0)
    tasks = start(tasks, TaskKey.READ_ADVERT, at=T0)
    tasks = advance(tasks, TaskKey.READ_CV, units_done=1, units_total=2)
    tasks = advance(tasks, TaskKey.READ_ADVERT, units_done=1, units_total=4)
    assert summarise(tasks).fraction == pytest.approx(0.75 / 7)
    baselines = {key: TaskBaseline(seconds=30) for key in TaskKey}
    assert estimate_remaining(tasks, now=_at(10), baselines=baselines) == 30 + 5 * 30


def test_call_plan_counts_attempts_and_late_repairs() -> None:
    tasks = plan_calls(plan_for(PipelineVersion.V2), TaskKey.JUDGE, model=2)
    tasks = call_finished(tasks, TaskKey.JUDGE, operation="model")
    tasks = plan_calls(tasks, TaskKey.JUDGE, model=1)
    judge = _task(tasks, TaskKey.JUDGE)
    assert (judge.model_calls_done, judge.model_calls_total) == (1, 3)
    with pytest.raises(ValueError):
        plan_calls(tasks, TaskKey.JUDGE, model=-1)
    with pytest.raises(ValueError):
        call_finished(tasks, TaskKey.JUDGE, operation="unknown")


def test_remaining_calls_ignore_skipped_work_and_mark_undiscovered_stages() -> None:
    tasks = plan_calls(
        plan_for(PipelineVersion.V2), TaskKey.READ_CV, model=2, embedding=1
    )
    tasks = call_finished(tasks, TaskKey.READ_CV, operation="model")
    tasks = plan_calls(tasks, TaskKey.RECHECK, model=5)
    tasks = skip(tasks, TaskKey.RECHECK, at=T0)
    view = progress_view(
        state=JobState.RUNNING,
        started_at=T0,
        finished_at=None,
        tasks=tasks,
        now=T0,
        baselines={},
    )
    assert (view.model_calls_done, view.model_calls_remaining) == (1, 1)
    assert view.embedding_calls_remaining == 1
    assert not view.call_estimate_complete
