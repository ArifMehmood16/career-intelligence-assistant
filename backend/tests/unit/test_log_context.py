"""Job context on every log line, including worker threads (spec 013, FR-001)."""

from __future__ import annotations

import io
import logging
from collections.abc import Iterator

import pytest

from career_assistant.application.providers.fanout import map_in_order
from career_assistant.logconfig import bind_log_context, configure_logging, log_event

_log = logging.getLogger("career_assistant.test_context")


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    buffer = io.StringIO()
    configure_logging(force=True, stream=buffer, level=logging.DEBUG)
    yield buffer
    configure_logging(force=True, level=logging.INFO)


def _lines(buffer: io.StringIO) -> list[str]:
    return [line for line in buffer.getvalue().splitlines() if line]


def test_bound_fields_are_appended_to_every_line(stream: io.StringIO) -> None:
    with bind_log_context(job_id="job-1", role_id="role-1"):
        log_event(_log, "inside")
    log_event(_log, "outside")

    inside, outside = _lines(stream)
    assert inside.endswith("job_id=job-1 role_id=role-1")
    assert "job_id=" not in outside


def test_nested_bindings_add_fields_and_restore_on_exit(stream: io.StringIO) -> None:
    with bind_log_context(job_id="job-1"):
        with bind_log_context(task="judge"):
            log_event(_log, "nested")
        log_event(_log, "outer")

    nested, outer = _lines(stream)
    assert nested.endswith("job_id=job-1 task=judge")
    assert outer.endswith("job_id=job-1")


def test_a_field_already_in_the_message_is_not_repeated(stream: io.StringIO) -> None:
    with bind_log_context(job_id="job-1", role_id="role-1"):
        log_event(_log, "worker.stage", job_id="job-1")

    (line,) = _lines(stream)
    assert line.count("job_id=job-1") == 1
    assert line.endswith("role_id=role-1")


def test_worker_threads_keep_the_job_context(stream: io.StringIO) -> None:
    def emit(index: int) -> int:
        log_event(_log, "batch", index=index)
        return index

    with bind_log_context(job_id="job-1"):
        map_in_order([1, 2, 3], emit, parallel=True, max_workers=3)

    lines = _lines(stream)
    assert len(lines) == 3
    assert all(line.endswith("job_id=job-1") for line in lines)
