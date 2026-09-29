"""Chunking contracts: the model groups server-numbered lines (ADR 013).

A chunk is a line range; its text is always the stored text. Fields the product
treats as the document's words (technology surface forms, skills, titles, dates,
quotes) are checked verbatim by the server after parsing. Kinds are closed per
document type, so a cover-letter aspiration can never arrive as CV experience.
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


class _Chunk(Contract):
    first_line: int = Field(ge=1, description="First line number of the chunk.")
    last_line: int = Field(
        ge=1, description="Last line number of the chunk, inclusive."
    )
    context: str | None = Field(
        default=None,
        max_length=300,
        description="One sentence placing this chunk in the document, for search only.",
    )
    skills: list[NonEmpty] = Field(
        default_factory=list, description="Skills named in the chunk, as written."
    )
    tech_terms: list[TechTerm] = Field(default_factory=list)


class CvChunk(_Chunk):
    kind: CvChunkKind
    role: RoleFields | None = Field(
        default=None, description="Only on role_heading chunks."
    )
    role_ref: int | None = Field(
        default=None,
        ge=1,
        description="First line of the role_heading this chunk belongs to.",
    )


class CoverLetterChunk(_Chunk):
    kind: CoverLetterChunkKind


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


class JobChunk(_Chunk):
    kind: JobChunkKind
    atomic_requirements: list[AtomicRequirement] = Field(
        default_factory=list,
        description="Only on requirement and responsibility chunks.",
    )


class CvChunkingResponse(VersionedContract):
    contract_version = "cv-chunking-v1"
    chunks: list[CvChunk] = Field(min_length=1)


class CoverLetterChunkingResponse(VersionedContract):
    contract_version = "cover-letter-chunking-v1"
    chunks: list[CoverLetterChunk] = Field(min_length=1)


class JobChunkingResponse(VersionedContract):
    contract_version = "job-chunking-v1"
    chunks: list[JobChunk] = Field(min_length=1)
