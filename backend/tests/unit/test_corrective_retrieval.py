"""Corrective retrieval: one bounded rewrite per requirement (ADR 014, PLAN 18.8)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from tests.support.in_memory_verdicts import InMemoryVerdictCache
from tests.support.recording_progress import RecordingProgress
from tests.support.scripted_structured import ScriptedStructured

from career_assistant.application.contracts.judge import JudgeResponse
from career_assistant.application.judge.cache import ModelIdentity
from career_assistant.application.judge.matching import (
    CandidateSearchResult,
    EvidenceMatcher,
)
from career_assistant.application.judge.prompt import JudgeLimits
from career_assistant.application.judge.service import RequirementJudge
from career_assistant.domain.candidate_facts import CandidateFacts
from career_assistant.domain.judging import Candidate, RequirementPacket
from career_assistant.domain.search import SearchHit

AS_OF = date(2026, 9, 1)
FACTS = CandidateFacts(terms=(), roles=())
SKILLS = Candidate("c-skills", "skills", "cv", "Python, pgvector")
DELIVERY = Candidate(
    "c-delivery", "experience", "cv", "Shipped semantic search on pgvector."
)


def _requirement(requirement_id: str) -> RequirementPacket:
    return RequirementPacket(
        requirement_id=requirement_id,
        quote="Vector search in production",
        statement="Has run vector search in production.",
        must_have=True,
        terms=("pgvector",),
        candidates=(),
    )


def _found(*candidates: Candidate) -> CandidateSearchResult:
    hits = tuple(
        SearchHit(c.chunk_id, 1.0 / (61 + rank), rank + 1, None, None)
        for rank, c in enumerate(candidates)
    )
    return CandidateSearchResult(hits=hits, candidates=candidates)


@dataclass
class FakeSearch:
    """Round 0 finds the skills line; the rewrite named in `finds` finds more."""

    finds: dict[str, CandidateSearchResult] = field(default_factory=dict)
    queries: list[tuple[str, str]] = field(default_factory=list)
    batches: list[tuple[str, ...]] = field(default_factory=list)

    def find(
        self, requirement: RequirementPacket, query_text: str
    ) -> CandidateSearchResult:
        self.queries.append((requirement.requirement_id, query_text))
        return self.finds.get(query_text, _found(SKILLS))

    def find_all(
        self, items: Sequence[tuple[RequirementPacket, str]]
    ) -> tuple[CandidateSearchResult, ...]:
        self.batches.append(tuple(text for _, text in items))
        return tuple(self.find(requirement, text) for requirement, text in items)


def _verdict(
    requirement_id: str, *, sufficient: bool, **changes: Any
) -> dict[str, Any]:
    verdict: dict[str, Any] = {
        "requirement_id": requirement_id,
        "verdict": "partial",
        "match": {
            "score": 2,
            "rationale": "Only a skills line.",
            "evidence": [{"chunk_id": "c-skills", "quote": "pgvector"}],
        },
        "retrieval_feedback": {
            "sufficient": sufficient,
            "rewrite_query": None if sufficient else f"{requirement_id} delivery",
        },
    }
    verdict.update(changes)
    return verdict


def _met(requirement_id: str) -> dict[str, Any]:
    return _verdict(
        requirement_id,
        sufficient=True,
        verdict="met",
        match={
            "score": 3,
            "rationale": "Shipped it.",
            "evidence": [{"chunk_id": "c-delivery", "quote": "semantic search"}],
        },
    )


def _reply(*verdicts: dict[str, Any]) -> JudgeResponse:
    return JudgeResponse.model_validate({"verdicts": list(verdicts)})


def _matcher(
    structured: ScriptedStructured, search: FakeSearch, *, max_rewrites: int = 5
) -> EvidenceMatcher:
    judge = RequirementJudge(
        structured,
        InMemoryVerdictCache(),
        ModelIdentity("scripted", "scripted-v1"),
        JudgeLimits(),
    )
    return EvidenceMatcher(search, judge, max_rewrites=max_rewrites)


def test_sufficient_evidence_is_searched_and_judged_once() -> None:
    search = FakeSearch()
    structured = ScriptedStructured([_reply(_verdict("r1", sufficient=True))])

    outcome = _matcher(structured, search).match(
        [_requirement("r1")], FACTS, as_of=AS_OF
    )

    assert search.queries == [("r1", "Has run vector search in production.")]
    assert len(structured.requests) == 1
    (only,) = outcome.traces["r1"]
    assert (only.round, only.query_text) == (0, "Has run vector search in production.")
    assert [h.chunk_id for h in only.hits] == ["c-skills"]


def test_a_rewrite_that_finds_the_evidence_is_judged_again_with_both_sets() -> None:
    search = FakeSearch(finds={"r1 delivery": _found(DELIVERY, SKILLS)})
    structured = ScriptedStructured(
        [_reply(_verdict("r1", sufficient=False)), _reply(_met("r1"))]
    )

    outcome = _matcher(structured, search).match(
        [_requirement("r1")], FACTS, as_of=AS_OF
    )

    assert search.queries[1] == ("r1", "r1 delivery")
    rejudge = structured.requests[1].user
    assert rejudge.index('<chunk id="c-skills">') < rejudge.index(
        '<chunk id="c-delivery">'
    )
    assert rejudge.count('<chunk id="c-skills">') == 1
    assert outcome.verdicts["r1"].verdict.verdict == "met"
    rounds = outcome.traces["r1"]
    assert [(r.round, r.query_text) for r in rounds] == [
        (0, "Has run vector search in production."),
        (1, "r1 delivery"),
    ]


def test_a_rewrite_that_finds_nothing_new_keeps_the_verdict_without_a_call() -> None:
    search = FakeSearch()
    structured = ScriptedStructured([_reply(_verdict("r1", sufficient=False))])

    outcome = _matcher(structured, search).match(
        [_requirement("r1")], FACTS, as_of=AS_OF
    )

    assert len(structured.requests) == 1
    assert outcome.verdicts["r1"].verdict.match_score == 2
    assert [r.round for r in outcome.traces["r1"]] == [0, 1]


def test_each_requirement_gets_one_rewrite_at_most() -> None:
    search = FakeSearch(finds={"r1 delivery": _found(DELIVERY)})
    again = _verdict(
        "r1",
        sufficient=False,
        retrieval_feedback={"sufficient": False, "rewrite_query": "still more"},
    )
    structured = ScriptedStructured(
        [_reply(_verdict("r1", sufficient=False)), _reply(again)]
    )

    outcome = _matcher(structured, search).match(
        [_requirement("r1")], FACTS, as_of=AS_OF
    )

    assert [q for _, q in search.queries] == [
        "Has run vector search in production.",
        "r1 delivery",
    ]
    assert len(structured.requests) == 2
    assert len(outcome.traces["r1"]) == 2


def test_the_analysis_cap_bounds_the_rewrites_in_requirement_order() -> None:
    search = FakeSearch()
    structured = ScriptedStructured(
        [
            _reply(
                _verdict("r1", sufficient=False),
                _verdict("r2", sufficient=False),
                _verdict("r3", sufficient=False),
            )
        ]
    )

    outcome = _matcher(structured, search, max_rewrites=2).match(
        [_requirement("r1"), _requirement("r2"), _requirement("r3")],
        FACTS,
        as_of=AS_OF,
    )

    rewrites = [q for _, q in search.queries if q.endswith("delivery")]
    assert rewrites == ["r1 delivery", "r2 delivery"]
    assert len(outcome.traces["r3"]) == 1
    assert outcome.rewrites == 2
    assert search.batches[0] == (
        "Has run vector search in production.",
        "Has run vector search in production.",
        "Has run vector search in production.",
    )
    assert search.batches[1] == ("r1 delivery", "r2 delivery")


def test_a_failed_re_judgement_keeps_the_validated_first_verdict() -> None:
    search = FakeSearch(finds={"r1 delivery": _found(DELIVERY)})
    broken = _verdict("r1", sufficient=True, verdict="missing")
    structured = ScriptedStructured(
        [_reply(_verdict("r1", sufficient=False)), _reply(broken), _reply(broken)]
    )

    outcome = _matcher(structured, search).match(
        [_requirement("r1")], FACTS, as_of=AS_OF
    )

    assert outcome.incomplete == ()
    assert outcome.verdicts["r1"].verdict.match_score == 2


def test_an_incomplete_requirement_is_not_searched_again() -> None:
    search = FakeSearch()
    broken = _verdict("r1", sufficient=False, verdict="missing")
    structured = ScriptedStructured([_reply(broken), _reply(broken)])

    outcome = _matcher(structured, search).match(
        [_requirement("r1")], FACTS, as_of=AS_OF
    )

    assert outcome.incomplete == ("r1",)
    assert len(search.queries) == 1


def test_progress_counts_searches_judgements_and_rechecks() -> None:
    progress = RecordingProgress()
    structured = ScriptedStructured(
        [
            _reply(
                _verdict("r1", sufficient=False),
                _verdict("r2", sufficient=False),
                _verdict("r3", sufficient=False),
            )
        ]
    )

    _matcher(structured, FakeSearch(), max_rewrites=2).match(
        [_requirement("r1"), _requirement("r2"), _requirement("r3")],
        FACTS,
        as_of=AS_OF,
        progress=progress,
    )

    assert progress.events == [
        ("enter", "search"),
        ("search", 0, 3),
        ("search", 1, 3),
        ("search", 2, 3),
        ("search", 3, 3),
        ("enter", "judge"),
        ("judge", 0, 3),
        ("plan_calls", "judge", 1, 0),
        ("judge", 3, 3),
        ("enter", "recheck"),
        ("recheck", 0, 2),
        ("recheck", 1, 2),
        ("recheck", 2, 2),
    ]


def test_progress_skips_the_recheck_when_the_evidence_was_enough() -> None:
    progress = RecordingProgress()
    structured = ScriptedStructured([_reply(_verdict("r1", sufficient=True))])

    _matcher(structured, FakeSearch()).match(
        [_requirement("r1")], FACTS, as_of=AS_OF, progress=progress
    )

    assert progress.events[-1] == ("skip", "recheck")


def test_corrective_requirements_with_new_evidence_share_one_rejudge_call() -> None:
    search = FakeSearch(
        finds={"r1 delivery": _found(DELIVERY), "r2 delivery": _found(DELIVERY)}
    )
    structured = ScriptedStructured(
        [
            _reply(_verdict("r1", sufficient=False), _verdict("r2", sufficient=False)),
            _reply(_met("r1"), _met("r2")),
        ]
    )
    outcome = _matcher(structured, search).match(
        [_requirement("r1"), _requirement("r2")], FACTS, as_of=AS_OF
    )
    assert len(structured.requests) == 2
    assert all(record.verdict.verdict == "met" for record in outcome.verdicts.values())
    assert '<requirement id="r1">' in structured.requests[1].user
    assert '<requirement id="r2">' in structured.requests[1].user
