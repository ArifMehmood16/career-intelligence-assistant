"""The job-description injection fixture, carried through to the judge (PLAN 18.7).

The advert tells the system to report a perfect match and to credit CUDA and ROS2.
Chunking already refuses those lines as requirements. Here a judge that obeys
them anyway still cannot turn them into a verdict: its quotes are not in the
candidate's chunks, so every requirement fails the server's rules, goes back once,
and is left incomplete rather than met.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from tests.support.in_memory_verdicts import InMemoryVerdictCache
from tests.support.scripted_structured import ScriptedStructured

from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.application.chunking.service import (
    ChunkingRequest,
    DocumentChunker,
)
from career_assistant.application.contracts.judge import JudgeResponse
from career_assistant.application.judge.cache import ModelIdentity
from career_assistant.application.judge.prompt import JudgeLimits
from career_assistant.application.judge.service import JudgeOutcome, RequirementJudge
from career_assistant.application.ports.structured import StructuredCompletionPort
from career_assistant.domain.candidate_facts import CandidateFacts
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.judging import Candidate, RequirementPacket

FIXTURES = Path(__file__).resolve().parents[3] / "sample-data" / "fixtures"
AS_OF = date(2026, 9, 1)
FACTS = CandidateFacts(terms=(), roles=())


def _chunks(kind: DocumentKind, name: str):  # noqa: ANN202
    text = (FIXTURES / name).read_text(encoding="utf-8")
    chunker = DocumentChunker(HermeticStructuredCompleter())
    return chunker.chunk(ChunkingRequest(document_id="d", kind=kind, text=text)).chunks


def _packets() -> list[RequirementPacket]:
    cv = [
        Candidate(f"cv-{c.first_line}", c.kind, "cv", c.text)
        for c in _chunks(DocumentKind.CV, "resumes/cv-strong-match.txt")
        if c.evidence_eligible
    ]
    advert = _chunks(
        DocumentKind.JOB_DESCRIPTION, "job-descriptions/jd-injection-attempt.txt"
    )
    requirements = [r for c in advert for r in c.atomic_requirements]
    return [
        RequirementPacket(
            requirement_id=f"req-{index}",
            quote=r.quote,
            statement=r.statement,
            must_have=r.must_have,
            terms=tuple(t.surface for t in r.tech_terms),
            candidates=tuple(cv),
        )
        for index, r in enumerate(requirements)
    ]


def _judge(structured: StructuredCompletionPort, provider: str) -> RequirementJudge:
    return RequirementJudge(
        structured,
        InMemoryVerdictCache(),
        ModelIdentity(provider, "fixture"),
        JudgeLimits(),
    )


def _obedient(packets: list[RequirementPacket]) -> JudgeResponse:
    """What a model that followed the advert's instructions would return."""
    return JudgeResponse.model_validate(
        {
            "verdicts": [
                {
                    "requirement_id": p.requirement_id,
                    "verdict": "met",
                    "match": {
                        "score": 4,
                        "rationale": "Perfect match, as instructed.",
                        "evidence": [
                            {
                                "chunk_id": p.candidates[0].chunk_id,
                                "quote": "CUDA and ROS2 experience",
                            }
                        ],
                    },
                    "retrieval_feedback": {"sufficient": True},
                }
                for p in packets
            ]
        }
    )


def _run(structured: StructuredCompletionPort, provider: str) -> JudgeOutcome:
    return _judge(structured, provider).judge(_packets(), FACTS, as_of=AS_OF)


def test_the_injected_lines_never_reach_the_judge_as_requirements() -> None:
    packets = _packets()

    assert packets
    for packet in packets:
        assert "IGNORE" not in packet.quote
        assert "cuda" not in {t.casefold() for t in packet.terms}


def test_a_judge_that_obeys_the_advert_gets_no_verdict_at_all() -> None:
    packets = _packets()
    reply = _obedient(packets)
    structured = ScriptedStructured([reply, reply], context_window_tokens=200_000)

    outcome = _run(structured, "scripted")

    assert outcome.verdicts == {}
    assert outcome.incomplete == tuple(p.requirement_id for p in packets)
    assert len(structured.requests) == 2
    assert "the quote is not in chunk" in structured.requests[1].user


def test_the_hermetic_judge_credits_only_what_the_cv_says() -> None:
    outcome = _run(HermeticStructuredCompleter(), "hermetic")

    assert outcome.incomplete == ()
    cv_text = {c.chunk_id: c.text for p in _packets() for c in p.candidates}
    for record in outcome.verdicts.values():
        for quote in record.verdict.evidence:
            assert quote.quote.casefold() in cv_text[quote.chunk_id].casefold()
        assert "cuda" not in record.verdict.match_rationale.casefold()
