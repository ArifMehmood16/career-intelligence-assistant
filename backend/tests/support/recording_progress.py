"""An AnalysisProgress that records what it was told, for asserting order."""

from __future__ import annotations

from dataclasses import dataclass, field

from career_assistant.domain.progress import TaskKey


@dataclass
class RecordingProgress:
    events: list[tuple[object, ...]] = field(default_factory=list)

    def enter(self, key: TaskKey) -> None:
        self.events.append(("enter", key.value))

    def start(self, key: TaskKey) -> None:
        self.events.append(("start", key.value))

    def finish(self, key: TaskKey) -> None:
        self.events.append(("finish", key.value))

    def plan_calls(self, key: TaskKey, *, model: int = 0, embedding: int = 0) -> None:
        self.events.append(("plan_calls", key.value, model, embedding))

    def call_finished(self, key: TaskKey, *, operation: str) -> None:
        self.events.append(("call_finished", key.value, operation))

    def count(self, key: TaskKey, done: int, total: int) -> None:
        self.events.append((key.value, done, total))

    def skip(self, key: TaskKey) -> None:
        self.events.append(("skip", key.value))

    @property
    def entered(self) -> list[object]:
        return [event[1] for event in self.events if event[0] == "enter"]
