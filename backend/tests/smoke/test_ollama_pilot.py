"""PLAN 13D.6 — labelled pilot on local Ollama. Not part of the default suite.

Run with RUN_LLM_SMOKE=1. The test checks that the measurement stays on this
machine. Accuracy figures are recorded from the observed output, not pinned here.
"""

from __future__ import annotations

import math
import os
from collections.abc import Sequence
from pathlib import Path

import pytest

from career_assistant.adapters.providers.httpx_transport import HttpxTransport
from career_assistant.adapters.providers.ollama.completion import (
    OllamaCompletionAdapter,
)
from career_assistant.adapters.providers.ollama.embedding import OllamaEmbeddingAdapter
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
)
from career_assistant.adapters.relatedness.model import ModelAdjudicator
from career_assistant.application.analysis.similarity import (
    InMemoryEmbeddingCache,
    requirement_claim_similarities,
)
from career_assistant.application.providers.accounting import (
    AccountingCompletion,
    AccountingEmbedding,
    CallAccountant,
)
from career_assistant.domain.assessment import PROMPT_VERSION
from career_assistant.domain.claims import Claim
from career_assistant.domain.requirements import Requirement
from career_assistant.evaluation.baseline import load_pilot, measured_policy_baseline

pytestmark = pytest.mark.smoke

ROOT = Path(__file__).resolve().parents[3]
DATASET = ROOT / "sample-data" / "evaluation" / "dataset.json"
# One variable at a time: change the completion model without touching the
# prompt or the labels, so a weak-model result can be told apart from a weak
# prompt. SMOKE_COMPLETION_MODEL / SMOKE_EMBEDDING_MODEL override the defaults.
_COMPLETION_MODEL = os.environ.get("SMOKE_COMPLETION_MODEL", "llama3.2")
_EMBEDDING_MODEL = os.environ.get("SMOKE_EMBEDDING_MODEL", "nomic-embed-text")


def _percentile(values: tuple[float, ...], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def test_local_ollama_measures_the_labelled_pilot() -> None:
    if os.environ.get("RUN_LLM_SMOKE") != "1":
        pytest.skip("set RUN_LLM_SMOKE=1 to measure local Ollama")
    transport = HttpxTransport()
    resilience = ResiliencePolicy(
        timeout_seconds=180,
        max_retries=1,
        breaker=CircuitBreaker(5),
    )
    accountant = CallAccountant()
    completion = AccountingCompletion(
        OllamaCompletionAdapter(
            base_url="http://127.0.0.1:11434",
            model_tag=_COMPLETION_MODEL,
            transport=transport,
            resilience=resilience,
        ),
        accountant,
        workspace_id="pilot",
        purpose="assess",
    )
    embedding = AccountingEmbedding(
        OllamaEmbeddingAdapter(
            base_url="http://127.0.0.1:11434",
            model_tag=_EMBEDDING_MODEL,
            transport=transport,
            resilience=resilience,
        ),
        accountant,
        workspace_id="pilot",
        purpose="embed",
    )
    cache = InMemoryEmbeddingCache()

    def similarities_for(
        requirements: Sequence[Requirement], claims: Sequence[Claim]
    ) -> dict[tuple[str, str], float]:
        return requirement_claim_similarities(
            workspace_id="pilot",
            requirements=requirements,
            claims=claims,
            embedding=embedding,
            cache=cache,
            provider_id="ollama",
            model_tag=_EMBEDDING_MODEL,
        )

    pilot = load_pilot(DATASET)
    report = measured_policy_baseline(
        pilot,
        adjudicator=ModelAdjudicator(completion),
        similarities_for=similarities_for,
    )
    assert report.calls_model is True
    assert report.role_latency_seconds
    assert accountant.records
    assert {record.provider_id for record in accountant.records} == {"ollama"}
    assert {record.left_machine for record in accountant.records} == {False}
    completions = [
        record for record in accountant.records if record.operation == "complete"
    ]
    embeddings = [
        record for record in accountant.records if record.operation == "embed"
    ]
    assert completions
    assert embeddings
    assert {record.model_tag for record in completions} == {_COMPLETION_MODEL}
    assert {record.model_tag for record in embeddings} == {_EMBEDDING_MODEL}
    lines = [
        f"completion_model={_COMPLETION_MODEL}",
        f"embedding_model={_EMBEDDING_MODEL}",
        f"prompt_version={PROMPT_VERSION}",
        f"roles={len(report.role_latency_seconds)}",
        f"disagreements={len(report.disagreements)}",
        f"unsupported_met={len(report.unsupported_met)}",
        f"order_disagreements={len(report.order_disagreements)}",
        f"retrieval_misses={len(report.retrieval_misses)}",
        f"p50_seconds={_percentile(report.role_latency_seconds, 0.50):.2f}",
        f"p95_seconds={_percentile(report.role_latency_seconds, 0.95):.2f}",
        f"completion_calls={len(completions)}",
        f"embedding_calls={len(embeddings)}",
    ]
    lines.extend(
        f"{item.role_id} {item.requirement_id} "
        f"expected={item.expected} observed={item.observed}"
        for item in report.disagreements
    )
    lines.extend(
        f"order {item.group_id} {item.ahead}={item.ahead_score} "
        f"{item.behind}={item.behind_score}"
        for item in report.order_disagreements
    )
    # A missing result means nothing until this list is empty: the requirement
    # may simply never have been shown its labelled supporting passage.
    lines.extend(
        f"retrieval miss {item.role_id} {item.requirement_id} "
        f"spans={','.join(item.span_ids)}"
        for item in report.retrieval_misses
    )
    print("\n".join(lines))
