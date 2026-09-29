"""The judge use case: cache, batches, server checks, one repair (ADR 014)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any

import pytest
from tests.support.in_memory_verdicts import InMemoryVerdictCache
from tests.support.scripted_structured import ScriptedStructured

from career_assistant.application.contracts.judge import JudgeResponse
from career_assistant.application.judge.cache import ModelIdentity
from career_assistant.application.judge.prompt import JudgeLimits
from career_assistant.application.judge.service import RequirementJudge
from career_assistant.application.ports.errors import (
    EgressNotPermittedError,
    ProviderRefusedError,
    StructuredOutputInvalidError,
    StructuredOutputTruncatedError,
)
from career_assistant.domain.candidate_facts import CandidateFacts
from career_assistant.domain.judging import Candidate, RequirementPacket

AS_OF = date(2026, 9, 1)
FACTS = CandidateFacts(terms=(), roles=())
MODEL = ModelIdentity("scripted", "scripted-v1")
TEXT = "Built hybrid retrieval over pgvector."


def _packet(requirement_id: str) -> RequirementPacket:
    return RequirementPacket(
        requirement_id=requirement_id,
        quote="Vector databases",
        statement="Has used a vector database.",
        must_have=True,
        terms=("pgvector",),
        candidates=(Candidate(f"c-{requirement_id}", "experience", "cv", TEXT),),
    )


def _verdict(requirement_id: str, **changes: Any) -> dict[str, Any]:
    verdict: dict[str, Any] = {
        "requirement_id": requirement_id,
        "verdict": "met",
        "match": {
            "score": 3,
            "rationale": "Built it.",
            "evidence": [{"chunk_id": f"c-{requirement_id}", "quote": "pgvector"}],
        },
        "retrieval_feedback": {"sufficient": True},
    }
    verdict.update(changes)
    return verdict


def _reply(*verdicts: dict[str, Any]) -> JudgeResponse:
    return JudgeResponse.model_validate({"verdicts": list(verdicts)})


def _judge(
    structured: ScriptedStructured,
    cache: InMemoryVerdictCache | None = None,
    limits: JudgeLimits | None = None,
) -> RequirementJudge:
    return RequirementJudge(
        structured,
        cache or InMemoryVerdictCache(),
        MODEL,
        limits or JudgeLimits(),
    )


def test_valid_verdicts_are_accepted_from_one_call() -> None:
    structured = ScriptedStructured([_reply(_verdict("r1"), _verdict("r2"))])

    outcome = _judge(structured).judge(
        [_packet("r1"), _packet("r2")], FACTS, as_of=AS_OF
    )

    assert outcome.incomplete == ()
    assert set(outcome.verdicts) == {"r1", "r2"}
    record = outcome.verdicts["r1"]
    assert (record.provider_id, record.model_tag, record.left_machine) == (
        "scripted",
        "scripted-v1",
        False,
    )
    assert record.cached is False
    assert len(structured.requests) == 1


def test_temperature_and_seed_are_sent_only_when_the_model_accepts_them() -> None:
    plain = ScriptedStructured([_reply(_verdict("r1"))])
    tunable = ScriptedStructured(
        [_reply(_verdict("r1"))], supports_temperature=True, supports_seed=True
    )

    _judge(plain).judge([_packet("r1")], FACTS, as_of=AS_OF)
    _judge(tunable).judge([_packet("r1")], FACTS, as_of=AS_OF)

    assert (plain.requests[0].temperature, plain.requests[0].seed) == (None, None)
    assert (tunable.requests[0].temperature, tunable.requests[0].seed) == (0.0, 0)


def test_a_broken_rule_gets_one_repair_call_for_that_requirement_only() -> None:
    paraphrased = _verdict(
        "r1",
        match={
            "score": 3,
            "rationale": "Built it.",
            "evidence": [{"chunk_id": "c-r1", "quote": "built pgvector search"}],
        },
    )
    structured = ScriptedStructured(
        [_reply(paraphrased, _verdict("r2")), _reply(_verdict("r1"))]
    )

    outcome = _judge(structured).judge(
        [_packet("r1"), _packet("r2")], FACTS, as_of=AS_OF
    )

    assert outcome.incomplete == ()
    repair = structured.requests[1].user
    assert '<requirement id="r1">' in repair
    assert '<requirement id="r2">' not in repair
    assert "- r1: evidence[0]: the quote is not in chunk c-r1 word for word" in repair


def test_a_requirement_still_invalid_after_the_repair_is_incomplete() -> None:
    wrong = _verdict("r1", verdict="missing")
    structured = ScriptedStructured([_reply(wrong, _verdict("r2")), _reply(wrong)])

    outcome = _judge(structured).judge(
        [_packet("r1"), _packet("r2")], FACTS, as_of=AS_OF
    )

    assert outcome.incomplete == ("r1",)
    assert set(outcome.verdicts) == {"r2"}
    assert len(structured.requests) == 2


def test_a_requirement_left_out_of_the_reply_is_repaired_like_any_other() -> None:
    structured = ScriptedStructured([_reply(_verdict("r2")), _reply(_verdict("r1"))])

    outcome = _judge(structured).judge(
        [_packet("r1"), _packet("r2")], FACTS, as_of=AS_OF
    )

    assert set(outcome.verdicts) == {"r1", "r2"}
    assert "- r1: no verdict was returned" in structured.requests[1].user


def test_a_reply_the_schema_repair_could_not_fix_is_incomplete_at_once() -> None:
    structured = ScriptedStructured(
        [
            StructuredOutputInvalidError(
                "bad", contract_version="judge-v1", error_count=2
            )
        ]
    )

    outcome = _judge(structured).judge([_packet("r1")], FACTS, as_of=AS_OF)

    assert outcome.incomplete == ("r1",)
    assert len(structured.requests) == 1


def test_a_refusal_leaves_the_batch_incomplete() -> None:
    structured = ScriptedStructured([ProviderRefusedError("no")])

    outcome = _judge(structured).judge([_packet("r1")], FACTS, as_of=AS_OF)

    assert outcome.incomplete == ("r1",)


def test_a_truncated_reply_splits_the_batch() -> None:
    structured = ScriptedStructured(
        [
            StructuredOutputTruncatedError("cut", contract_version="judge-v1"),
            _reply(_verdict("r1")),
            _reply(_verdict("r2")),
        ]
    )

    outcome = _judge(structured).judge(
        [_packet("r1"), _packet("r2")], FACTS, as_of=AS_OF
    )

    assert set(outcome.verdicts) == {"r1", "r2"}
    assert len(structured.requests) == 3


def test_a_single_requirement_cut_off_is_incomplete() -> None:
    structured = ScriptedStructured(
        [StructuredOutputTruncatedError("cut", contract_version="judge-v1")]
    )

    outcome = _judge(structured).judge([_packet("r1")], FACTS, as_of=AS_OF)

    assert outcome.incomplete == ("r1",)


def test_the_output_limit_splits_requirements_across_calls() -> None:
    structured = ScriptedStructured(
        [_reply(_verdict("r1")), _reply(_verdict("r2"))], max_output_tokens=400
    )

    outcome = _judge(structured).judge(
        [_packet("r1"), _packet("r2")], FACTS, as_of=AS_OF
    )

    assert set(outcome.verdicts) == {"r1", "r2"}
    assert len(structured.requests) == 2
    assert structured.requests[0].max_output_tokens == 400


def test_an_unchanged_requirement_reuses_its_cached_verdict() -> None:
    cache = InMemoryVerdictCache()
    _judge(ScriptedStructured([_reply(_verdict("r1"))]), cache).judge(
        [_packet("r1")], FACTS, as_of=AS_OF
    )
    again = replace(_packet("r1"), requirement_id="r1-reextracted")
    structured = ScriptedStructured([])

    outcome = _judge(structured, cache).judge([again], FACTS, as_of=AS_OF)

    record = outcome.verdicts["r1-reextracted"]
    assert record.cached is True
    assert record.verdict.requirement_id == "r1-reextracted"
    assert structured.requests == []


def test_a_verdict_from_a_fallback_model_is_not_cached() -> None:
    cache = InMemoryVerdictCache()
    fallback = ScriptedStructured([_reply(_verdict("r1"))], model_tag="other-model")

    outcome = _judge(fallback, cache).judge([_packet("r1")], FACTS, as_of=AS_OF)

    assert outcome.verdicts["r1"].model_tag == "other-model"
    assert cache.size == 0


def test_a_closed_egress_gate_is_not_an_incomplete_verdict() -> None:
    structured = ScriptedStructured([EgressNotPermittedError("closed")])

    with pytest.raises(EgressNotPermittedError):
        _judge(structured).judge([_packet("r1")], FACTS, as_of=AS_OF)


def test_the_prompt_labels_document_text_untrusted() -> None:
    structured = ScriptedStructured([_reply(_verdict("r1"))])

    _judge(structured).judge([_packet("r1")], FACTS, as_of=AS_OF)

    request = structured.requests[0]
    assert request.contract is JudgeResponse
    assert "untrusted" in request.system
    assert request.user.index("<candidate_facts>") < request.user.index(TEXT)
