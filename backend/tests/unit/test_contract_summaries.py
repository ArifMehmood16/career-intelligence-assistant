"""Model responses describe themselves for logs without their text (spec 013)."""

from __future__ import annotations

from typing import Any

from career_assistant.application.contracts.chunking import (
    CvChunkResponse,
    JobChunkResponse,
)
from career_assistant.application.contracts.judge import JudgeResponse

_PRIVATE = "PRIVATE words from the documents"


def _verdict(label: str, *, sufficient: bool = True) -> dict[str, Any]:
    feedback: dict[str, Any] = {"sufficient": sufficient}
    if not sufficient:
        feedback["rewrite_query"] = _PRIVATE
    return {
        "requirement_id": "r1",
        "verdict": label,
        "match": {"score": 3, "rationale": _PRIVATE, "evidence": []},
        "retrieval_feedback": feedback,
    }


def _term() -> dict[str, str]:
    return {"surface": _PRIVATE, "canonical": "kubernetes"}


def test_a_judge_response_counts_verdicts_by_label() -> None:
    response = JudgeResponse.model_validate(
        {
            "verdicts": [
                _verdict("met"),
                _verdict("met"),
                _verdict("partial", sufficient=False),
                _verdict("missing"),
            ]
        }
    )

    assert response.log_summary() == (
        "4 verdicts (2 met, 1 partial, 1 missing; 1 asks for more evidence)"
    )


def test_an_advert_reply_counts_chunks_requirements_and_terms() -> None:
    requirement = {"quote": _PRIVATE, "statement": _PRIVATE, "must_have": True}
    response = JobChunkResponse.model_validate(
        {
            "chunks": [
                {
                    "first_line": 1,
                    "last_line": 2,
                    "kind": "requirement",
                    "atomic_requirements": [
                        requirement,
                        {**requirement, "must_have": False},
                    ],
                    "tech_terms": [_term()],
                },
                {"first_line": 3, "last_line": 3, "kind": "benefit"},
            ]
        }
    )

    summary = response.log_summary()

    assert summary == (
        "2 chunks, 2 requirements (1 must-have), 1 tech term, 0 taxonomy entries"
    )
    assert _PRIVATE not in summary


def test_a_cv_reply_counts_chunks_roles_and_terms() -> None:
    response = CvChunkResponse.model_validate(
        {
            "chunks": [
                {
                    "first_line": 1,
                    "last_line": 1,
                    "kind": "role_heading",
                    "role": {"title": _PRIVATE},
                },
                {
                    "first_line": 2,
                    "last_line": 4,
                    "kind": "experience",
                    "role_ref": 1,
                    "tech_terms": [_term(), _term()],
                },
            ]
        }
    )

    assert response.log_summary() == (
        "2 chunks, 1 role, 2 tech terms, 0 taxonomy entries"
    )
