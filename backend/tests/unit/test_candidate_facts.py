"""Graph facts the judge sees for each required term (ADR 014, PLAN 18.7)."""

from __future__ import annotations

from datetime import date

from career_assistant.domain.candidate_facts import Coverage, candidate_facts
from career_assistant.domain.chunking import (
    Chunk,
    ProposedChunk,
    RoleProposal,
    TechTermProposal,
    validate_chunk_plan,
)
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.lines import number_lines
from career_assistant.domain.recency import DateRange

AS_OF = date(2026, 9, 1)
CV = (
    "Senior Data Engineer, Northwind, Jan 2023 – Present\n"
    "Built retrieval over pgvector and Postgres.\n"
)


def _cv() -> tuple[Chunk, ...]:
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
                    date_text="Jan 2023 – Present",
                    seniority_level="senior",
                ),
            ),
            ProposedChunk(
                first_line=2,
                last_line=2,
                kind="experience",
                role_ref=1,
                tech_terms=(
                    TechTermProposal("pgvector", "pgvector"),
                    TechTermProposal("Postgres", "postgresql"),
                ),
            ),
        ],
    )
    assert plan.problems == ()
    return plan.chunks


def test_a_term_written_as_in_the_advert_is_exact_with_its_years() -> None:
    facts = candidate_facts(
        _cv(), [TechTermProposal("pgvector", "pgvector")], as_of=AS_OF
    )

    (term,) = facts.terms
    assert (term.term, term.coverage) == ("pgvector", Coverage.EXACT)
    assert term.experience.months == 45


def test_a_different_spelling_of_the_same_technology_is_alias_only() -> None:
    facts = candidate_facts(
        _cv(), [TechTermProposal("PostgreSQL", "postgresql")], as_of=AS_OF
    )

    (term,) = facts.terms
    assert term.coverage == Coverage.ALIAS
    assert term.experience.months == 0


def test_a_term_the_cv_never_names_is_missing() -> None:
    facts = candidate_facts(_cv(), [TechTermProposal("Qdrant", "qdrant")], as_of=AS_OF)

    assert facts.terms[0].coverage == Coverage.MISSING


def test_a_term_required_twice_is_reported_once() -> None:
    pgvector = TechTermProposal("pgvector", "pgvector")

    facts = candidate_facts(_cv(), [pgvector, pgvector], as_of=AS_OF)

    assert len(facts.terms) == 1


def test_each_role_reports_its_level_and_dates() -> None:
    facts = candidate_facts(_cv(), [], as_of=AS_OF)

    (role,) = facts.roles
    assert (role.title, role.employer, role.level) == (
        "Senior Data Engineer",
        "Northwind",
        "senior",
    )
    assert role.dates == DateRange(date(2023, 1, 1), None)
