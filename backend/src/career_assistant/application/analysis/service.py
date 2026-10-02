"""Worker lifetime types shared by the current analysis adapters."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

JobClock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class StartupRecovery:
    failed_job_ids: tuple[str, ...]
    dispatched_job_ids: tuple[str, ...]
