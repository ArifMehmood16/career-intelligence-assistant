"""In-memory call accounting — identifiers and counts only."""

from __future__ import annotations

from career_assistant.application.ports.types import CallRecord


class CallAccountant:
    def __init__(self) -> None:
        self._records: list[CallRecord] = []

    def record(self, entry: CallRecord) -> None:
        self._records.append(entry)

    @property
    def records(self) -> tuple[CallRecord, ...]:
        return tuple(self._records)
