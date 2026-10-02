"""A test-only verdict cache held in a dictionary."""

from __future__ import annotations

from career_assistant.application.ports.verdicts import VerdictRecord


class InMemoryVerdictCache:
    def __init__(self) -> None:
        self._records: dict[str, VerdictRecord] = {}

    @property
    def size(self) -> int:
        return len(self._records)

    def find(self, key: str) -> VerdictRecord | None:
        return self._records.get(key)

    def keep(self, key: str, record: VerdictRecord) -> None:
        self._records[key] = record
