"""Validated verdicts and their cache, keyed on everything the judge saw."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from career_assistant.domain.judging import JudgedVerdict


@dataclass(frozen=True, slots=True)
class VerdictRecord:
    verdict: JudgedVerdict
    input_hash: str
    provider_id: str
    model_tag: str
    left_machine: bool
    cached: bool = False


class VerdictCache(Protocol):
    def find(self, key: str) -> VerdictRecord | None: ...

    def keep(self, key: str, record: VerdictRecord) -> None: ...
