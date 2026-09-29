"""Whether a running analysis may still call a provider (role or CV deleted)."""

from __future__ import annotations

from collections.abc import Callable

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ports.errors import JobCancelled
from career_assistant.domain.jobs import LIVE_STATES, AnalysisJob


class SqlJobLiveness:
    """A cancellation check for one job: raises JobCancelled once it has gone.

    Deleting the role deletes the job row; deleting or replacing the CV fails it.
    Either way the next provider call is not made. One indexed read per call is
    small next to a model call.
    """

    def __init__(
        self, uow_factory: Callable[[], SqlUnitOfWork], job: AnalysisJob
    ) -> None:
        self._uow_factory = uow_factory
        self._workspace_id = job.workspace_id
        self._job_id = job.id

    def __call__(self) -> None:
        with self._uow_factory() as uow:
            current = uow.jobs.get(self._workspace_id, self._job_id)
        if current is None or current.state not in LIVE_STATES:
            raise JobCancelled(self._job_id)
