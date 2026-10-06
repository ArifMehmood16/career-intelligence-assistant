"""Map a validated chunking contract onto the domain's proposals."""

from __future__ import annotations

from collections.abc import Sequence

from career_assistant.application.contracts.base import TechTerm
from career_assistant.application.contracts.chunking import (
    AtomicRequirement,
    CvChunk,
    DocumentChunk,
    JobChunk,
)
from career_assistant.domain.chunking import (
    AtomicRequirementProposal,
    ProposedChunk,
    RoleProposal,
    TechTermProposal,
)


def proposals_from_chunks(chunks: Sequence[DocumentChunk]) -> tuple[ProposedChunk, ...]:
    return tuple(_proposal(chunk) for chunk in chunks)


def _proposal(chunk: DocumentChunk) -> ProposedChunk:
    role = chunk.role if isinstance(chunk, CvChunk) else None
    return ProposedChunk(
        first_line=chunk.first_line,
        last_line=chunk.last_line,
        kind=chunk.kind,
        context=chunk.context,
        skills=tuple(chunk.skills),
        tech_terms=_terms(chunk.tech_terms),
        role=None
        if role is None
        else RoleProposal(
            employer=role.employer,
            title=role.title,
            date_text=role.date_text,
            seniority_level=role.seniority_level,
        ),
        role_ref=chunk.role_ref if isinstance(chunk, CvChunk) else None,
        atomic_requirements=tuple(
            _requirement(item) for item in chunk.atomic_requirements
        )
        if isinstance(chunk, JobChunk)
        else (),
    )


def _requirement(item: AtomicRequirement) -> AtomicRequirementProposal:
    return AtomicRequirementProposal(
        quote=item.quote,
        statement=item.statement,
        must_have=item.must_have,
        years_expected=item.years_expected,
        seniority_expected=item.seniority_expected,
        experience_expected=item.experience_expected,
        tech_terms=_terms(item.tech_terms),
    )


def _terms(terms: list[TechTerm]) -> tuple[TechTermProposal, ...]:
    return tuple(
        TechTermProposal(surface=term.surface, canonical=term.canonical)
        for term in terms
    )
