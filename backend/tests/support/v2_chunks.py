"""Validated v2 chunks for a small CV and advert, shared by v2 tests."""

from __future__ import annotations

from career_assistant.domain.chunking import (
    AtomicRequirementProposal,
    Chunk,
    ProposedChunk,
    RoleProposal,
    TechTermProposal,
    validate_chunk_plan,
)
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.lines import number_lines

CV = (
    "Senior Data Engineer, Northwind, Mar 2021 – Dec 2024\n"
    "Built retrieval over Postgres and Python.\n"
    "Skills: Kafka\n"
)
JD = "5+ years of Python and Postgres\n"


def cv_chunks() -> tuple[Chunk, ...]:
    plan = validate_chunk_plan(
        DocumentKind.CV,
        number_lines(CV),
        CV,
        [
            ProposedChunk(
                first_line=1,
                last_line=1,
                kind="role_heading",
                role=RoleProposal(
                    employer="Northwind",
                    title="Senior Data Engineer",
                    date_text="Mar 2021 – Dec 2024",
                    seniority_level="senior",
                ),
            ),
            ProposedChunk(
                first_line=2,
                last_line=2,
                kind="experience",
                context="Data platform work at Northwind.",
                role_ref=1,
                tech_terms=(
                    TechTermProposal(surface="Postgres", canonical="postgresql"),
                    TechTermProposal(surface="Python", canonical="python"),
                ),
            ),
            ProposedChunk(
                first_line=3,
                last_line=3,
                kind="skills",
                skills=("Kafka",),
                tech_terms=(TechTermProposal(surface="Kafka", canonical="kafka"),),
            ),
        ],
    )
    assert plan.problems == ()
    return plan.chunks


def jd_chunks() -> tuple[Chunk, ...]:
    requirement = AtomicRequirementProposal(
        quote="5+ years of Python and Postgres",
        statement="5+ years of Python",
        must_have=True,
        years_expected=5.0,
        seniority_expected="senior",
        tech_terms=(TechTermProposal(surface="Python", canonical="python"),),
    )
    plan = validate_chunk_plan(
        DocumentKind.JOB_DESCRIPTION,
        number_lines(JD),
        JD,
        [
            ProposedChunk(
                first_line=1,
                last_line=1,
                kind="requirement",
                atomic_requirements=(requirement,),
            )
        ],
    )
    assert plan.problems == ()
    return plan.chunks
