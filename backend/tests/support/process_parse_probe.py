"""Picklable probes for real parser-worker lifecycle acceptance tests."""

import os
import time
from multiprocessing import active_children
from pathlib import Path
from typing import NoReturn

from career_assistant.application.ports.intake import UploadDocument
from career_assistant.parsing.process_pool import _parse, _ParseResult


def reporting_parse(upload: UploadDocument) -> _ParseResult:
    Path(upload.filename).write_text(str(os.getpid()), encoding="utf-8")
    return _parse(upload)


def stalled_parse(upload: UploadDocument) -> _ParseResult:
    Path(upload.filename).write_text(str(os.getpid()), encoding="utf-8")
    time.sleep(30)
    return _parse(upload)


def crashed_parse(upload: UploadDocument) -> NoReturn:
    Path(upload.filename).write_text(str(os.getpid()), encoding="utf-8")
    os._exit(17)


def assert_worker_stopped(marker: Path) -> None:
    """Allow asynchronous termination to settle, checking only our synthetic PID."""
    pid = int(marker.read_text(encoding="utf-8"))
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        active_children()  # Reap exited children before checking their PID.
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.01)
    raise AssertionError(f"synthetic parser worker {pid} is still running")
