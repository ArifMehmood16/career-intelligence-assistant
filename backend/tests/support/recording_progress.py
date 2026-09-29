"""An AnalysisProgress that records what it was told, for asserting order."""

from __future__ import annotations

from dataclasses import dataclass, field

from career_assistant.domain.progress import TaskKey


@dataclass
class RecordingProgress:
    events: list[tuple[object, ...]] = field(default_factory=list)

    def enter(self, key: TaskKey) -> None:
        self.events.append(("enter", key.value))

    def count(self, key: TaskKey, done: int, total: int) -> None:
        self.events.append((key.value, done, total))

    def skip(self, key: TaskKey) -> None:
        self.events.append(("skip", key.value))

    @property
    def entered(self) -> list[object]:
        return [event[1] for event in self.events if event[0] == "enter"]
