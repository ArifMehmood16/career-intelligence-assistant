"""Shared pieces of every model-call contract."""

from __future__ import annotations

from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    """Extra properties are errors, so the schema says additionalProperties: false."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class VersionedContract(Contract):
    """A top-level response. Its version joins prompt and cache keys."""

    contract_version: ClassVar[str]

    def log_summary(self) -> str:
        """Describe the reply for a log line: counts and labels, never its text."""
        sized = [
            counted(len(value), name.removesuffix("s"))
            for name, value in self
            if isinstance(value, list)
        ]
        return ", ".join(sized) or type(self).__name__


def counted(number: int, noun: str, plural: str | None = None) -> str:
    """``1 chunk``, ``2 chunks``; for content-free log summaries."""
    word = noun if number == 1 else (plural or f"{noun}s")
    return f"{number} {word}"


NonEmpty = Annotated[str, Field(min_length=1)]

SeniorityLevel = Literal[
    "intern", "junior", "mid", "senior", "lead", "principal", "director"
]


class TechTerm(Contract):
    surface: NonEmpty = Field(
        description="The technology exactly as written in the text, same spelling."
    )
    canonical: NonEmpty = Field(
        description="The usual lowercase name of that technology, e.g. postgresql."
    )
