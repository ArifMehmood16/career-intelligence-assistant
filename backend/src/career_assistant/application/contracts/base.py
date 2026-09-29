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
