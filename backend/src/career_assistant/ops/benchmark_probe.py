"""Content-free measurement at provider boundaries, safe across worker threads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from threading import Lock
from typing import Final, Literal

from career_assistant.adapters.providers.http_transport import (
    HttpResponse,
    HttpTransport,
)
from career_assistant.application.ports.progress import NoProgress
from career_assistant.application.ports.types import CapabilityDescriptor
from career_assistant.domain.progress import TaskKey

Operation = Literal["completion", "embedding", "metadata"]
COMPLETION: Final = "completion"
EMBEDDING: Final = "embedding"
METADATA: Final = "metadata"
STRUCTURED: Final = "structured"


@dataclass(frozen=True, slots=True)
class ProbeSnapshot:
    physical_attempts: dict[str, int]
    logical_operations: dict[str, int]
    progress_attempts: dict[str, int]
    cache_reuse: dict[str, int]
    capabilities: dict[str, dict[str, object]]
    observed_providers: tuple[tuple[str, str, bool], ...]
    selected_configuration: dict[str, object]

    def payload(self) -> dict[str, object]:
        return asdict(self)


class BenchmarkProbe(NoProgress):
    """Existing accounting writes progress; transport writes real request attempts."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._physical = dict.fromkeys((COMPLETION, EMBEDDING, METADATA), 0)
            self._logical = dict.fromkeys((STRUCTURED, EMBEDDING), 0)
            self._progress: dict[str, int] = {}
            self._reuse = dict.fromkeys(
                ("documents", "vectors", "verdict_lookups", "verdict_hits"), 0
            )
            self._capabilities: dict[str, dict[str, object]] = {}
            self._observed: set[tuple[str, str, bool]] = set()
            self._selected: dict[str, object] = {}

    def physical(self, operation: Operation) -> None:
        with self._lock:
            self._physical[operation] += 1

    def logical(self, operation: str) -> None:
        with self._lock:
            self._logical[operation] += 1

    def reuse(self, kind: str, count: int = 1) -> None:
        with self._lock:
            self._reuse[kind] += count

    def capability(self, operation: str, value: CapabilityDescriptor) -> None:
        with self._lock:
            self._capabilities[operation] = asdict(value)

    def observe(self, provider: str, model: str, left_machine: bool) -> None:
        with self._lock:
            self._observed.add((provider, model, left_machine))

    def select(self, configuration: dict[str, object]) -> None:
        with self._lock:
            self._selected = dict(configuration)

    def call_finished(self, key: TaskKey, *, operation: str) -> None:
        label = f"{key.value}.{operation}"
        with self._lock:
            self._progress[label] = self._progress.get(label, 0) + 1

    def snapshot(self) -> ProbeSnapshot:
        with self._lock:
            return ProbeSnapshot(
                dict(self._physical),
                dict(self._logical),
                dict(self._progress),
                dict(self._reuse),
                dict(self._capabilities),
                tuple(sorted(self._observed)),
                dict(self._selected),
            )


class MeasuredTransport:
    """Count before dispatch, retaining failed requests without their payloads."""

    def __init__(
        self,
        inner: HttpTransport,
        probe: BenchmarkProbe,
        *,
        operation: Literal["completion", "embedding"],
    ) -> None:
        self._inner = inner
        self._probe = probe
        self._operation = operation

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
        timeout_seconds: float,
    ) -> HttpResponse:
        operation: Operation = METADATA if method.upper() == "GET" else self._operation
        self._probe.physical(operation)
        return self._inner.request(
            method,
            url,
            headers=headers,
            json_body=json_body,
            timeout_seconds=timeout_seconds,
        )
