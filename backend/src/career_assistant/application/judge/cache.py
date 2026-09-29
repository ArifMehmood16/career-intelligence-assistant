"""The verdict cache key (ADR 014, PLAN 18.7).

A verdict is reused only when everything the judge saw is the same: the prompt,
anchor and contract versions, the model down to its digest where the provider
exposes one, the requirement, its facts, the analysis date, and the candidates in
order with a hash of their text. The requirement's id is not in the key, so a
re-extracted but unchanged requirement reuses its verdict. The rubric is not in it
either: aggregation is recomputed from the verdicts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from career_assistant.application.contracts.judge import JudgeResponse
from career_assistant.application.judge.prompt import (
    JUDGE_ANCHOR_VERSION,
    JUDGE_PROMPT_VERSION,
)
from career_assistant.domain.candidate_facts import CandidateFacts, TermFact
from career_assistant.domain.judging import Candidate, RequirementPacket
from career_assistant.domain.knowledge_graph import normalise_term
from career_assistant.domain.recency import DateRange


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    provider_id: str
    model_tag: str
    model_digest: str | None = None


def verdict_key(
    packet: RequirementPacket,
    facts: CandidateFacts,
    model: ModelIdentity,
    *,
    as_of: date,
) -> str:
    named = {normalise_term(term) for term in packet.terms}
    inputs = {
        "versions": [
            JUDGE_PROMPT_VERSION,
            JUDGE_ANCHOR_VERSION,
            JudgeResponse.contract_version,
        ],
        "model": [model.provider_id, model.model_tag, model.model_digest],
        "as_of": as_of.isoformat(),
        "requirement": [
            packet.quote,
            packet.statement,
            packet.must_have,
            packet.years_expected,
            packet.seniority_expected,
            list(packet.terms),
        ],
        "terms": [_term(t) for t in facts.terms if t.term in named],
        "roles": [[r.title, r.employer, r.level, _span(r.dates)] for r in facts.roles],
        "candidates": [_candidate(c) for c in packet.candidates],
    }
    canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _term(term: TermFact) -> list[Any]:
    fact = term.experience
    last = fact.last_used.isoformat() if fact.last_used else None
    return [
        term.term,
        term.coverage.value,
        fact.months,
        fact.dated_roles,
        fact.undated_roles,
        last,
        fact.ongoing,
    ]


def _candidate(candidate: Candidate) -> list[Any]:
    text = hashlib.sha256(candidate.text.encode("utf-8")).hexdigest()
    return [
        candidate.chunk_id,
        text,
        candidate.kind,
        candidate.source,
        candidate.role,
        _span(candidate.dates),
    ]


def _span(span: DateRange | None) -> list[str | None] | None:
    if span is None:
        return None
    return [span.start.isoformat(), span.end.isoformat() if span.end else None]
