"""Synthetic timing uses the current pipeline and honest request accounting.

Authored under deferred verification; no test result is claimed for this change.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from tests.support.refusing_structured import RefusingJudge
from tests.support.scripted_transport import ScriptedTransport
from tests.support.sequence_transport import SequenceTransport

from career_assistant.adapters.providers.http_transport import HttpResponse
from career_assistant.adapters.providers.resilience import (
    CircuitBreaker,
    ResiliencePolicy,
    classify_http_status,
)
from career_assistant.application.ports.errors import ProviderUnavailableError
from career_assistant.ops import benchmark_runtime
from career_assistant.ops.benchmark import main, run_benchmark
from career_assistant.ops.benchmark_cases import load_dataset
from career_assistant.ops.benchmark_probe import BenchmarkProbe, MeasuredTransport
from career_assistant.ops.benchmark_runtime import BenchmarkConfig


def test_cold_warm_runs_reuse_the_current_analysis_caches() -> None:
    report = run_benchmark(
        BenchmarkConfig(repetitions=2, as_of=date(2026, 9, 1)),
        load_dataset(["clean_match"]),
    )

    assert report.measurement_kind == "fixture"
    assert len(report.observations) == 4
    for cold, warm in zip(
        report.observations[::2], report.observations[1::2], strict=True
    ):
        assert cold.temperature == "cold" and warm.temperature == "warm"
        assert cold.status == warm.status == "succeeded"
        assert cold.score == warm.score
        assert cold.requirement_count == warm.requirement_count > 0
        assert cold.requirement_ids == warm.requirement_ids
        assert cold.elapsed_seconds is not None and cold.elapsed_seconds >= 0
        assert warm.elapsed_seconds is not None and warm.elapsed_seconds >= 0
        assert cold.counts.physical_attempts == {
            "completion": 0,
            "embedding": 0,
            "metadata": 0,
        }
        assert warm.counts.physical_attempts == cold.counts.physical_attempts
        assert cold.counts.cache_reuse["documents"] == 0
        assert warm.counts.cache_reuse["documents"] == 2
        assert warm.counts.cache_reuse["vectors"] > 0
        assert warm.counts.cache_reuse["verdict_hits"] > 0
        assert warm.counts.logical_operations["structured"] == 0
        # Query embeddings still run even when document vectors are reused.
        assert warm.counts.logical_operations["embedding"] > 0
        assert cold.counts.selected_configuration == warm.counts.selected_configuration


def test_reports_fingerprint_inputs_without_serializing_their_contents() -> None:
    dataset = load_dataset(["clean_match"])
    report = run_benchmark(BenchmarkConfig(), dataset)
    encoded = json.dumps(report.payload())

    case = dataset.cases[0]
    assert json.dumps(case.cv_text)[1:-1] not in encoded
    assert json.dumps(case.jd_text)[1:-1] not in encoded
    assert case.cv_text.splitlines()[2] not in encoded
    assert case.jd_text.splitlines()[2] not in encoded
    assert case.cv_sha256 in encoded and case.jd_sha256 in encoded
    assert report.schema_version == "analysis-benchmark-v1"
    assert report.prompts["chunking"] and report.prompts["judge"]
    assert "rubric_sha256" in report.fingerprints
    assert "models_sha256" in report.fingerprints
    assert report.source["revision"] is not None


def test_incomplete_analysis_is_recorded_without_a_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(benchmark_runtime, "HermeticStructuredCompleter", RefusingJudge)
    report = run_benchmark(BenchmarkConfig(), load_dataset(["clean_match"]))

    cold, warm = report.observations
    assert cold.status == "failed" and cold.score is None and cold.band is None
    assert cold.error_code == "assessment_incomplete"
    assert cold.counts.logical_operations["structured"] > 0
    assert warm.status == "skipped" and warm.elapsed_seconds is None
    assert not report.succeeded
    assert report.summaries[0].successful_runs == 0
    assert report.summaries[0].p50_seconds is None


def test_each_transport_retry_is_counted_once_without_payloads() -> None:
    probe = BenchmarkProbe()
    transport = MeasuredTransport(
        SequenceTransport(
            [
                HttpResponse(503, b"private provider response", {}),
                HttpResponse(200, b"{}", {}),
            ]
        ),
        probe,
        operation="completion",
    )
    resilience = ResiliencePolicy(
        timeout_seconds=1,
        max_retries=1,
        breaker=CircuitBreaker(5),
        sleep=lambda _: None,
    )

    def attempt() -> HttpResponse:
        response = transport.request(
            "POST",
            "https://example.invalid/private-endpoint",
            headers={"Authorization": "private-key"},
            json_body={"text": "private prompt"},
            timeout_seconds=1,
        )
        classify_http_status(response.status_code, response.headers)
        return response

    resilience.run(attempt)
    snapshot = probe.snapshot()
    assert snapshot.physical_attempts["completion"] == 2
    assert snapshot.logical_operations["structured"] == 0
    assert "private" not in json.dumps(snapshot.payload())


def test_failed_transport_attempt_and_metadata_lookup_are_not_lost() -> None:
    probe = BenchmarkProbe()
    transport = MeasuredTransport(
        SequenceTransport([ProviderUnavailableError("private failure")]),
        probe,
        operation="completion",
    )
    with pytest.raises(ProviderUnavailableError):
        transport.request("GET", "http://example.invalid/api/tags", timeout_seconds=1)
    assert probe.snapshot().physical_attempts["metadata"] == 1


@pytest.mark.parametrize("repetitions", [0, 21])
def test_repeat_limit_is_enforced(repetitions: int) -> None:
    with pytest.raises(ValueError, match="repetitions"):
        BenchmarkConfig(repetitions=repetitions)


def test_unknown_case_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown_case"):
        load_dataset(["private-cv"])


def test_escaping_manifest_filename_is_rejected_before_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from career_assistant.ops import benchmark_cases

    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "version": 1,
                "pairings": [
                    {"id": "escape", "cv": "../private.txt", "job": "job.txt"}
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(benchmark_cases, "FIXTURES", tmp_path)
    with pytest.raises(ValueError, match="invalid_fixture_name"):
        load_dataset(["escape"])


def test_probe_updates_survive_parallel_threads() -> None:
    from concurrent.futures import ThreadPoolExecutor

    probe = BenchmarkProbe()
    with ThreadPoolExecutor(max_workers=4) as pool:
        tuple(pool.map(lambda _: probe.physical("completion"), range(100)))
    assert probe.snapshot().physical_attempts["completion"] == 100


def test_live_selection_requires_opt_in_before_settings_are_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_settings() -> None:
        pytest.fail("settings must not be read without live opt-in")

    monkeypatch.setattr(benchmark_runtime, "ProviderSettings", forbidden_settings)
    assert main(["--provider", "openai", "--case", "clean_match"]) == 2


def test_closed_hosted_gate_refuses_before_any_transport_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from career_assistant.settings import ProviderSettings

    settings = ProviderSettings(
        _env_file=None,
        allow_hosted_providers=False,
        openai_api_key=None,
        anthropic_api_key=None,
    )
    monkeypatch.setattr(benchmark_runtime, "ProviderSettings", lambda: settings)
    transport = ScriptedTransport({})
    report = run_benchmark(
        BenchmarkConfig(live=True, provider="openai", embedding_provider="ollama"),
        load_dataset(["clean_match"]),
        transport=transport,
    )
    assert not report.succeeded
    assert report.observations[0].error_code == "egress_not_permitted"
    assert transport.calls == []


def test_existing_output_is_preserved_before_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "existing.json"
    output.write_text("keep me", encoding="utf-8")

    def unexpected_run(*args: object, **kwargs: object) -> None:
        pytest.fail("refuse an existing output before starting work")

    monkeypatch.setattr("career_assistant.ops.benchmark.run_benchmark", unexpected_run)
    assert main(["--case", "clean_match", "--output", str(output)]) == 2
    assert output.read_text(encoding="utf-8") == "keep me"
