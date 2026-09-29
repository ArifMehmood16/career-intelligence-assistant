"""The hermetic structured fixture keeps v2 tests offline (PLAN 18.4).

It is a test fixture, not a product default: rules good enough to exercise the
pipeline on the synthetic fixtures, never presented as model quality.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from tests.support.in_memory_verdicts import InMemoryVerdictCache

from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.application.chunking.service import (
    ChunkingRequest,
    DocumentChunker,
)
from career_assistant.application.contracts.agent import AgentAnswer
from career_assistant.application.graph.taxonomy import TermTaxonomist
from career_assistant.application.judge.cache import ModelIdentity
from career_assistant.application.judge.prompt import JudgeLimits
from career_assistant.application.judge.service import RequirementJudge
from career_assistant.application.ports.errors import ProviderUnavailableError
from career_assistant.application.ports.structured import StructuredRequest
from career_assistant.domain.candidate_facts import CandidateFacts, Coverage, TermFact
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.experience import ExperienceFact
from career_assistant.domain.judging import (
    Candidate,
    JudgedVerdict,
    ProposedQuote,
    RequirementPacket,
)

FIXTURES = Path(__file__).resolve().parents[3] / "sample-data" / "fixtures"
CVS = sorted((FIXTURES / "resumes").glob("*.txt"))
JDS = sorted((FIXTURES / "job-descriptions").glob("*.txt"))


def _chunk(kind: DocumentKind, text: str):  # noqa: ANN202
    chunker = DocumentChunker(HermeticStructuredCompleter())
    return chunker.chunk(ChunkingRequest(document_id="d", kind=kind, text=text))


@pytest.mark.parametrize("path", CVS, ids=[p.stem for p in CVS])
def test_every_synthetic_cv_chunks_without_a_repair(path: Path) -> None:
    outcome = _chunk(DocumentKind.CV, path.read_text(encoding="utf-8"))

    assert outcome.repairs == 0
    assert outcome.provider_id == "hermetic"
    assert any(c.kind == "experience" for c in outcome.chunks)


@pytest.mark.parametrize("path", JDS, ids=[p.stem for p in JDS])
def test_every_synthetic_advert_chunks_without_a_repair(path: Path) -> None:
    outcome = _chunk(DocumentKind.JOB_DESCRIPTION, path.read_text(encoding="utf-8"))

    assert outcome.repairs == 0
    assert any(c.atomic_requirements for c in outcome.chunks)


def test_a_role_heading_and_its_bullets_are_linked() -> None:
    text = (
        "EXPERIENCE\n"
        "Cedar Metrics Co — BI Analyst\n"
        "June 2021 – Present\n"
        "- Built Power BI dashboards for support SLAs\n"
        "and ticket volume.\n"
    )

    chunks = _chunk(DocumentKind.CV, text).chunks

    assert [(c.first_line, c.last_line, c.kind) for c in chunks] == [
        (1, 1, "other"),
        (2, 3, "role_heading"),
        (4, 5, "experience"),
    ]
    assert chunks[2].role_ref == 2


def test_contact_lines_are_contact_and_never_evidence() -> None:
    text = "Jane Doe\nEmail: jane@example.com\nSKILLS\nPython, SQL\n"

    chunks = _chunk(DocumentKind.CV, text).chunks

    assert [c.kind for c in chunks] == ["contact", "contact", "other", "skills"]
    assert not any(c.evidence_eligible for c in chunks[:2])
    assert [t.surface for t in chunks[3].tech_terms] == ["Python", "SQL"]


def test_an_instruction_in_an_advert_is_not_a_requirement() -> None:
    text = (FIXTURES / "job-descriptions" / "jd-injection-attempt.txt").read_text(
        encoding="utf-8"
    )

    chunks = _chunk(DocumentKind.JOB_DESCRIPTION, text).chunks

    quotes = [r.quote for c in chunks for r in c.atomic_requirements]
    assert not any("IGNORE" in q or "CUDA" in q for q in quotes)
    desirable = [
        r for c in chunks for r in c.atomic_requirements if "Looker" in r.quote
    ]
    assert desirable and desirable[0].must_have is False


def test_the_fixture_is_deterministic() -> None:
    text = CVS[0].read_text(encoding="utf-8")

    assert _chunk(DocumentKind.CV, text) == _chunk(DocumentKind.CV, text)


def test_the_taxonomy_fixture_answers_every_term_with_no_relations() -> None:
    outcome = TermTaxonomist(HermeticStructuredCompleter()).relate(
        ["pgvector", "python"]
    )

    assert outcome.failure is None
    assert outcome.edges == ()
    assert outcome.provider_id == "hermetic"


def test_a_contract_with_no_fixture_is_refused() -> None:
    with pytest.raises(ProviderUnavailableError):
        HermeticStructuredCompleter().complete_structured(
            StructuredRequest(
                contract=AgentAnswer, system="s", user="u", max_output_tokens=10
            )
        )


def _judge_packet(text: str, **changes: object) -> RequirementPacket:
    packet = RequirementPacket(
        requirement_id="r1",
        quote="5+ years of pgvector",
        statement="Five years with pgvector.",
        must_have=True,
        terms=("pgvector",),
        candidates=(Candidate("c1", "experience", "cv", text),),
    )
    return replace(packet, **changes)  # type: ignore[arg-type]


def _judged(packet: RequirementPacket, facts: CandidateFacts) -> JudgedVerdict:
    judge = RequirementJudge(
        HermeticStructuredCompleter(),
        InMemoryVerdictCache(),
        ModelIdentity("hermetic", "rules-v1"),
        JudgeLimits(),
    )
    outcome = judge.judge([packet], facts, as_of=date(2026, 9, 1))
    assert outcome.incomplete == ()
    return outcome.verdicts[packet.requirement_id].verdict


def test_the_judge_fixture_quotes_a_named_term_as_written() -> None:
    verdict = _judged(
        _judge_packet("Built retrieval over PGVector."), CandidateFacts((), ())
    )

    assert (verdict.verdict, verdict.match_score) == ("met", 3)
    assert verdict.evidence == (ProposedQuote("c1", "PGVector"),)


def test_the_judge_fixture_scores_years_from_the_facts() -> None:
    fact = ExperienceFact(30, 1, 0, None, ongoing=False)
    facts = CandidateFacts((TermFact("pgvector", Coverage.EXACT, fact),), ())
    packet = _judge_packet("Built retrieval over pgvector.", years_expected=5.0)

    verdict = _judged(packet, facts)

    assert verdict.experience_score == 2


def test_the_judge_fixture_finds_nothing_for_an_unnamed_term() -> None:
    verdict = _judged(_judge_packet("Wrote Kafka consumers."), CandidateFacts((), ()))

    assert (verdict.verdict, verdict.match_score, verdict.evidence) == (
        "missing",
        0,
        (),
    )
