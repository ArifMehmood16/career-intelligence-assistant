"""One structured document response with ranges and extraction fields (ADR 013).

The server checks coverage and every quoted field against stored text.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from career_assistant.application.contracts.base import (
    Contract,
    NonEmpty,
    SeniorityLevel,
    TechTerm,
    VersionedContract,
)
from career_assistant.application.contracts.taxonomy import TermRelations

CvChunkKind = Literal[
    "role_heading",
    "experience",
    "project",
    "skills",
    "qualification",
    "summary",
    "contact",
    "other",
]
CoverLetterChunkKind = Literal["experience", "aspiration", "motivation", "other"]
JobChunkKind = Literal[
    "requirement", "responsibility", "benefit", "logistics", "about", "other"
]


class RoleFields(Contract):
    employer: str | None = Field(default=None, description="As written in the heading.")
    title: str | None = Field(default=None, description="As written in the heading.")
    date_text: str | None = Field(
        default=None,
        description="The date range exactly as written, e.g. Mar 2021 – Dec 2024.",
    )
    seniority_level: SeniorityLevel | None = Field(
        default=None, description="Your reading of the title's level."
    )


class _Bounds(Contract):
    first_line: int = Field(ge=1, description="First line number of the chunk.")
    last_line: int = Field(
        ge=1, description="Last line number of the chunk, inclusive."
    )


class ChunkFields(Contract):
    context: str | None = Field(
        default=None,
        max_length=300,
        description="One sentence placing this chunk in the document, for search only.",
    )
    skills: list[NonEmpty] = Field(
        default_factory=list, description="Skills named in the chunk, as written."
    )
    tech_terms: list[TechTerm] = Field(default_factory=list)


class AtomicRequirement(Contract):
    quote: NonEmpty = Field(description="The clause exactly as written in the advert.")
    statement: NonEmpty = Field(
        description="One assessable requirement in your words, for search only."
    )
    must_have: bool
    years_expected: float | None = Field(
        default=None, ge=0, le=50, description="Only when the advert states a number."
    )
    seniority_expected: SeniorityLevel | None = Field(
        default=None, description="Only when the advert or its title states a level."
    )
    tech_terms: list[TechTerm] = Field(default_factory=list)


class CvChunk(_Bounds, ChunkFields):
    kind: CvChunkKind
    role: RoleFields | None = Field(default=None, description="Only on role_heading.")
    role_ref: int | None = Field(default=None, ge=1)


class CoverLetterChunk(_Bounds, ChunkFields):
    kind: CoverLetterChunkKind


class JobChunk(_Bounds, ChunkFields):
    kind: JobChunkKind
    atomic_requirements: list[AtomicRequirement] = Field(default_factory=list)


class CvChunkResponse(VersionedContract):
    contract_version = "cv-chunks-v2"
    chunks: list[CvChunk] = Field(min_length=1)
    taxonomy: list[TermRelations] = Field(default_factory=list)


class CoverLetterChunkResponse(VersionedContract):
    contract_version = "cover-letter-chunks-v2"
    chunks: list[CoverLetterChunk] = Field(min_length=1)
    taxonomy: list[TermRelations] = Field(default_factory=list)


class JobChunkResponse(VersionedContract):
    contract_version = "job-chunks-v2"
    chunks: list[JobChunk] = Field(min_length=1)
    taxonomy: list[TermRelations] = Field(default_factory=list)


DocumentChunk = CvChunk | CoverLetterChunk | JobChunk
DocumentChunkResponse = CvChunkResponse | CoverLetterChunkResponse | JobChunkResponse
