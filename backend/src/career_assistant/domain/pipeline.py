"""Which matching pipeline an analysis runs (PLAN 18.10, ADR 013)."""

from __future__ import annotations

from enum import StrEnum


class PipelineVersion(StrEnum):
    V1 = "v1"
    V2 = "v2"
