"""Admission errors and safe codes for document intake."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IntakeErrorCode(StrEnum):
    DOCUMENT_TOO_LARGE = "document_too_large"
    DOCUMENT_UNSUPPORTED = "document_unsupported"
    DOCUMENT_UNREADABLE = "document_unreadable"


@dataclass(frozen=True, slots=True)
class IntakeError(Exception):
    code: IntakeErrorCode
    message: str

    def __str__(self) -> str:
        return self.message
