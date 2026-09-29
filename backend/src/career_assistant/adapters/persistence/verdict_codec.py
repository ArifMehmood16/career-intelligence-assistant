"""A validated verdict as JSON in match_verdicts.payload, and back (PLAN 18.10)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from career_assistant.domain.judging import (
    Adjustment,
    JudgedVerdict,
    ProposedQuote,
    ProposedScore,
    VerdictLabel,
)


def verdict_payload(verdict: JudgedVerdict, *, left_machine: bool) -> dict[str, Any]:
    return {
        "verdict": verdict.verdict,
        "match_score": verdict.match_score,
        "match_rationale": verdict.match_rationale,
        "evidence": [
            {"chunk_id": q.chunk_id, "quote": q.quote} for q in verdict.evidence
        ],
        "seniority": _score_json(verdict.seniority),
        "experience": _score_json(verdict.experience),
        "unmet_conditions": list(verdict.unmet_conditions),
        "contradiction": verdict.contradiction,
        "sufficient": verdict.sufficient,
        "rewrite_query": verdict.rewrite_query,
        "adjustments": [a.value for a in verdict.adjustments],
        "left_machine": left_machine,
    }


def verdict_from_payload(
    requirement_id: str, payload: Mapping[str, Any]
) -> JudgedVerdict:
    return JudgedVerdict(
        requirement_id=requirement_id,
        verdict=cast(VerdictLabel, payload["verdict"]),
        match_score=int(payload["match_score"]),
        match_rationale=str(payload["match_rationale"]),
        evidence=tuple(
            ProposedQuote(chunk_id=str(q["chunk_id"]), quote=str(q["quote"]))
            for q in payload["evidence"]
        ),
        seniority=_score(payload["seniority"]),
        experience=_score(payload["experience"]),
        unmet_conditions=tuple(str(c) for c in payload["unmet_conditions"]),
        contradiction=bool(payload["contradiction"]),
        sufficient=bool(payload["sufficient"]),
        rewrite_query=payload["rewrite_query"],
        adjustments=tuple(Adjustment(a) for a in payload["adjustments"]),
    )


def _score_json(score: ProposedScore | None) -> dict[str, Any] | None:
    if score is None:
        return None
    return {"score": score.score, "rationale": score.rationale}


def _score(item: Mapping[str, Any] | None) -> ProposedScore | None:
    if item is None:
        return None
    return ProposedScore(score=int(item["score"]), rationale=str(item["rationale"]))
