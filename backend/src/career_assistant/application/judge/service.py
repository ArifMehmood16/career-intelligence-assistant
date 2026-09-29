"""Judge atomic requirements against retrieved evidence (ADR 014, PLAN 18.7).

The model proposes verdicts; `domain.judging` decides which stand. A requirement
that breaks a server rule goes back once, with the problems listed. A requirement
still invalid after that, or in a batch the provider could not answer, is
incomplete — the analysis then publishes no score, never a low one. A provider that
is unavailable or not permitted is not a verdict at all, so that error propagates.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date

from career_assistant.application.contracts.judge import (
    DimensionJudgement,
    JudgeResponse,
    RequirementVerdict,
)
from career_assistant.application.judge.cache import ModelIdentity, verdict_key
from career_assistant.application.judge.prompt import (
    JUDGE_SYSTEM,
    JudgeLimits,
    judge_batches,
    judge_user,
    render_facts,
)
from career_assistant.application.ports.errors import (
    ProviderInputTooLargeError,
    ProviderRefusedError,
    ProviderTransientError,
    StructuredOutputError,
    StructuredOutputTruncatedError,
)
from career_assistant.application.ports.structured import (
    StructuredCompletionPort,
    StructuredRequest,
    StructuredResult,
)
from career_assistant.application.ports.verdicts import VerdictCache, VerdictRecord
from career_assistant.domain.candidate_facts import CandidateFacts
from career_assistant.domain.judging import (
    ProposedQuote,
    ProposedScore,
    ProposedVerdict,
    RequirementPacket,
    check_verdicts,
)

# Truncation is handled first, by splitting the batch.
_UNANSWERED = (
    StructuredOutputError,
    ProviderRefusedError,
    ProviderTransientError,
    ProviderInputTooLargeError,
)
_REPAIR_OPENING = "Your previous verdicts broke these rules:"
_REPAIR_CLOSING = (
    "Return one verdict for each requirement above, following every rule, "
    "as the complete JSON object."
)


@dataclass(frozen=True, slots=True)
class JudgeOutcome:
    verdicts: Mapping[str, VerdictRecord]
    incomplete: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Context:
    facts: CandidateFacts
    as_of: date
    keys: Mapping[str, str]


class RequirementJudge:
    def __init__(
        self,
        structured: StructuredCompletionPort,
        cache: VerdictCache,
        model: ModelIdentity,
        limits: JudgeLimits,
    ) -> None:
        self._structured = structured
        self._cache = cache
        self._model = model
        self._limits = limits

    def judge(
        self,
        packets: Sequence[RequirementPacket],
        facts: CandidateFacts,
        *,
        as_of: date,
        on_judged: Callable[[int], None] | None = None,
    ) -> JudgeOutcome:
        """Judge every packet. `on_judged` hears how many have been handled."""
        report = on_judged or _ignore
        capabilities = self._structured.capabilities
        model = replace(self._model, model_digest=capabilities.model_digest)
        keys = {
            p.requirement_id: verdict_key(p, facts, model, as_of=as_of) for p in packets
        }
        context = _Context(facts=facts, as_of=as_of, keys=keys)
        records: dict[str, VerdictRecord] = {}
        pending: list[RequirementPacket] = []
        for packet in packets:
            hit = self._cache.find(keys[packet.requirement_id])
            if hit is None:
                pending.append(packet)
            else:
                records[packet.requirement_id] = _rebound(hit, packet.requirement_id)
        handled = len(packets) - len(pending)
        report(handled)
        prefix = len(render_facts(facts, as_of=as_of))
        for batch in judge_batches(
            pending, capabilities, self._limits, prefix_chars=prefix
        ):
            records.update(self._judge_batch(batch, context))
            handled += len(batch)
            report(handled)
        incomplete = tuple(
            p.requirement_id for p in packets if p.requirement_id not in records
        )
        return JudgeOutcome(verdicts=records, incomplete=incomplete)

    def _judge_batch(
        self, batch: Sequence[RequirementPacket], context: _Context
    ) -> dict[str, VerdictRecord]:
        user = judge_user(context.facts, batch, as_of=context.as_of)
        try:
            result = self._call(user)
        except StructuredOutputTruncatedError:
            return self._split(batch, context)
        except _UNANSWERED:
            return {}
        records, problems = self._accept(batch, result, context)
        failed = [p for p in batch if p.requirement_id in problems]
        if failed:
            records.update(self._repair(failed, problems, context))
        return records

    def _split(
        self, batch: Sequence[RequirementPacket], context: _Context
    ) -> dict[str, VerdictRecord]:
        if len(batch) == 1:
            return {}
        half = len(batch) // 2
        return {
            **self._judge_batch(batch[:half], context),
            **self._judge_batch(batch[half:], context),
        }

    def _repair(
        self,
        failed: Sequence[RequirementPacket],
        problems: Mapping[str, tuple[str, ...]],
        context: _Context,
    ) -> dict[str, VerdictRecord]:
        listed = [
            f"- {p.requirement_id}: {problem}"
            for p in failed
            for problem in problems[p.requirement_id]
        ]
        user = "\n\n".join(
            [
                judge_user(context.facts, failed, as_of=context.as_of),
                "\n".join([_REPAIR_OPENING, *listed]),
                _REPAIR_CLOSING,
            ]
        )
        try:
            result = self._call(user)
        except _UNANSWERED:
            return {}
        records, _ = self._accept(failed, result, context)
        return records

    def _accept(
        self,
        batch: Sequence[RequirementPacket],
        result: StructuredResult[JudgeResponse],
        context: _Context,
    ) -> tuple[dict[str, VerdictRecord], Mapping[str, tuple[str, ...]]]:
        check = check_verdicts(batch, [_proposed(v) for v in result.value.verdicts])
        same_model = (result.provider_id, result.model_tag) == (
            self._model.provider_id,
            self._model.model_tag,
        )
        records: dict[str, VerdictRecord] = {}
        for requirement_id, verdict in check.verdicts.items():
            key = context.keys[requirement_id]
            record = VerdictRecord(
                verdict=verdict,
                input_hash=key,
                provider_id=result.provider_id,
                model_tag=result.model_tag,
                left_machine=result.left_machine,
            )
            if same_model:
                self._cache.keep(key, record)
            records[requirement_id] = record
        return records, check.problems

    def _call(self, user: str) -> StructuredResult[JudgeResponse]:
        capabilities = self._structured.capabilities
        request = StructuredRequest(
            contract=JudgeResponse,
            system=JUDGE_SYSTEM,
            user=user,
            max_output_tokens=min(
                capabilities.max_output_tokens, self._limits.max_output_tokens
            ),
            temperature=0.0 if capabilities.supports_temperature else None,
            seed=0 if capabilities.supports_seed else None,
        )
        return self._structured.complete_structured(request)


def _ignore(handled: int) -> None:
    del handled


def _rebound(record: VerdictRecord, requirement_id: str) -> VerdictRecord:
    verdict = replace(record.verdict, requirement_id=requirement_id)
    return replace(record, verdict=verdict, cached=True)


def _proposed(verdict: RequirementVerdict) -> ProposedVerdict:
    return ProposedVerdict(
        requirement_id=verdict.requirement_id,
        verdict=verdict.verdict,
        match=ProposedScore(verdict.match.score, verdict.match.rationale),
        evidence=tuple(
            ProposedQuote(q.chunk_id, q.quote) for q in verdict.match.evidence
        ),
        seniority=_score(verdict.seniority),
        experience=_score(verdict.experience),
        unmet_conditions=tuple(verdict.unmet_conditions),
        contradiction=verdict.contradiction,
        sufficient=verdict.retrieval_feedback.sufficient,
        rewrite_query=verdict.retrieval_feedback.rewrite_query,
    )


def _score(judgement: DimensionJudgement | None) -> ProposedScore | None:
    if judgement is None:
        return None
    return ProposedScore(judgement.score, judgement.rationale)
