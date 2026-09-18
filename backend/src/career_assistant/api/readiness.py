"""Readiness probe protocol — no SQLAlchemy in the HTTP package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ReadinessProbe(Protocol):
    @property
    def database(self) -> str: ...

    @property
    def migrations(self) -> str: ...

    @property
    def completion_provider(self) -> str: ...

    @property
    def embedding_provider(self) -> str: ...

    @property
    def hosted_egress(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class StaticReadiness:
    database: str
    migrations: str
    completion_provider: str
    embedding_provider: str
    hosted_egress: bool
