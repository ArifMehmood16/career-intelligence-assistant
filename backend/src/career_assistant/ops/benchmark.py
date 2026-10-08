"""Reproducible synthetic analysis timing; no execution implied by implementation."""

from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from time import perf_counter
from typing import Final, Literal, TextIO

from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.application.chunking.prompts import CHUNKING_PROMPT_VERSION
from career_assistant.application.chunking.service import ChunkingIncompleteError
from career_assistant.application.contracts.chunking import (
    CvChunkResponse,
    JobChunkResponse,
)
from career_assistant.application.contracts.judge import JudgeResponse
from career_assistant.application.judge.prompt import (
    JUDGE_ANCHOR_VERSION,
    JUDGE_PROMPT_VERSION,
)
from career_assistant.application.ports.errors import (
    EgressNotPermittedError,
    ProviderInputTooLargeError,
    ProviderRefusedError,
    ProviderTransientError,
    ProviderUnavailableError,
)
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric_v2
from career_assistant.ops.benchmark_cases import (
    ROOT,
    BenchmarkCase,
    BenchmarkDataset,
    fingerprint,
    load_dataset,
)
from career_assistant.ops.benchmark_probe import BenchmarkProbe, ProbeSnapshot
from career_assistant.ops.benchmark_quality import (
    QUALITY_CASES,
    JudgedLabel,
    QualityLabels,
    QualityMetrics,
    load_quality,
    measure,
    ranking_agreement,
)
from career_assistant.ops.benchmark_runtime import BenchmarkConfig, BenchmarkRuntime

Temperature = Literal["cold", "warm"]
Status = Literal["succeeded", "failed", "skipped"]
_SCHEMA = "analysis-benchmark-v1"
COLD: Final = "cold"
WARM: Final = "warm"
SUCCEEDED: Final = "succeeded"
FAILED: Final = "failed"
SKIPPED: Final = "skipped"


@dataclass(frozen=True, slots=True)
class _RunLabel:
    repetition: int
    temperature: Temperature


@dataclass(frozen=True, slots=True)
class Observation:
    case_id: str
    repetition: int
    temperature: Temperature
    status: Status
    elapsed_seconds: float | None
    counts: ProbeSnapshot
    requirement_count: int = 0
    requirement_ids: tuple[str, ...] = ()
    incomplete_count: int = 0
    score: float | None = None
    band: str | None = None
    error_code: str | None = None
    quality: QualityMetrics | None = None


@dataclass(frozen=True, slots=True)
class LatencySummary:
    case_id: str
    temperature: Temperature
    successful_runs: int
    failed_runs: int
    skipped_runs: int
    p50_seconds: float | None
    p95_seconds: float | None


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    schema_version: str
    measured_at: str
    measurement_kind: str
    scope: str
    configuration: dict[str, object]
    source: dict[str, str | bool | None]
    runtime: dict[str, str]
    fingerprints: dict[str, object]
    prompts: dict[str, str]
    observations: tuple[Observation, ...]
    summaries: tuple[LatencySummary, ...]
    quality: dict[str, object] | None = None

    @property
    def succeeded(self) -> bool:
        return bool(self.observations) and all(
            item.status == SUCCEEDED for item in self.observations
        )

    def payload(self) -> dict[str, object]:
        payload = asdict(self)
        if self.quality is None:
            payload.pop("quality")
            for item in payload["observations"]:
                item.pop("quality")
        return payload


def _error_code(error: Exception) -> str:
    for kind, code in (
        (EgressNotPermittedError, "egress_not_permitted"),
        (ProviderUnavailableError, "provider_unavailable"),
        (ProviderRefusedError, "provider_refused"),
        (ProviderTransientError, "provider_transient"),
        (ProviderInputTooLargeError, "provider_input_too_large"),
        (ChunkingIncompleteError, "chunking_incomplete"),
        (ValueError, "invalid_analysis"),
    ):
        if isinstance(error, kind):
            return code
    return "analysis_failed"


def _observe(
    config: BenchmarkConfig,
    case: BenchmarkCase,
    probe: BenchmarkProbe,
    label: _RunLabel,
    *,
    runtime: BenchmarkRuntime | None = None,
    transport: HttpTransport | None = None,
    quality_labels: QualityLabels | None = None,
) -> tuple[Observation, BenchmarkRuntime | None]:
    started = perf_counter()
    try:
        runtime = runtime or BenchmarkRuntime(config, case, probe, transport=transport)
        analysis = runtime.run(probe)
    except Exception as error:
        # Command boundary: unexpected failures also retain accounting, without
        # printing exceptions that might contain a provider payload or secret.
        return Observation(
            case.case_id,
            label.repetition,
            label.temperature,
            FAILED,
            perf_counter() - started,
            probe.snapshot(),
            error_code=_error_code(error),
        ), runtime
    publishable = analysis.fit.publishable and analysis.fit.score is not None
    error_code = None
    if not publishable:
        error_code = (
            "assessment_incomplete"
            if analysis.match.incomplete
            else "no_scoreable_requirements"
        )
    elapsed = perf_counter() - started
    quality = None
    if quality_labels is not None:
        expected = next(
            item for item in quality_labels.cases if item.case_id == case.case_id
        )
        judgments = []
        for item in analysis.requirements:
            record = analysis.match.verdicts.get(item.packet.requirement_id)
            judgments.append(
                JudgedLabel(
                    item.packet.quote, record.verdict.verdict if record else None
                )
            )
        quality = measure(expected, judgments)
    return Observation(
        case.case_id,
        label.repetition,
        label.temperature,
        SUCCEEDED if publishable else FAILED,
        elapsed,
        probe.snapshot(),
        len(analysis.requirements),
        tuple(item.packet.requirement_id for item in analysis.requirements),
        len(analysis.match.incomplete),
        analysis.fit.score if publishable else None,
        analysis.fit.band if publishable else None,
        error_code,
        quality,
    ), runtime


def _pair(
    config: BenchmarkConfig,
    case: BenchmarkCase,
    repetition: int,
    transport: HttpTransport | None,
    quality_labels: QualityLabels | None,
) -> tuple[Observation, Observation]:
    probe = BenchmarkProbe()
    cold, runtime = _observe(
        config,
        case,
        probe,
        _RunLabel(repetition, COLD),
        transport=transport,
        quality_labels=quality_labels,
    )
    probe.reset()
    if cold.status != SUCCEEDED:
        warm = Observation(
            case.case_id,
            repetition,
            WARM,
            SKIPPED,
            None,
            probe.snapshot(),
            error_code="cold_run_failed",
        )
    else:
        warm, _ = _observe(
            config,
            case,
            probe,
            _RunLabel(repetition, WARM),
            runtime=runtime,
            quality_labels=quality_labels,
        )
    return cold, warm


def _percentile(values: Sequence[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def _summaries(observations: Sequence[Observation]) -> tuple[LatencySummary, ...]:
    groups: dict[tuple[str, Temperature], list[Observation]] = {}
    for item in observations:
        groups.setdefault((item.case_id, item.temperature), []).append(item)
    summaries: list[LatencySummary] = []
    for (case_id, temperature), items in groups.items():
        elapsed = [
            item.elapsed_seconds
            for item in items
            if item.status == SUCCEEDED and item.elapsed_seconds is not None
        ]
        summaries.append(
            LatencySummary(
                case_id,
                temperature,
                len(elapsed),
                sum(item.status == FAILED for item in items),
                sum(item.status == SKIPPED for item in items),
                _percentile(elapsed, 0.5),
                _percentile(elapsed, 0.95),
            )
        )
    return tuple(summaries)


def _source() -> dict[str, str | bool | None]:
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except OSError, subprocess.SubprocessError:
        return {"revision": None, "dirty": None}
    return {"revision": revision, "dirty": bool(dirty)}


def _fingerprints(dataset: BenchmarkDataset) -> dict[str, object]:
    return {
        "manifest_sha256": dataset.manifest_sha256,
        "rubric_sha256": fingerprint(
            (ROOT / "config/scoring_rubric.toml").read_bytes()
        ),
        "models_sha256": fingerprint((ROOT / "config/models.toml").read_bytes()),
        "cases": [
            {
                "case_id": case.case_id,
                "cv_sha256": case.cv_sha256,
                "jd_sha256": case.jd_sha256,
            }
            for case in dataset.cases
        ],
    }


def run_benchmark(
    config: BenchmarkConfig,
    dataset: BenchmarkDataset,
    *,
    transport: HttpTransport | None = None,
    quality_labels: QualityLabels | None = None,
) -> BenchmarkReport:
    # Capture provenance before work, so filesystem/git activity is outside timing.
    source, fingerprints = _source(), _fingerprints(dataset)
    if quality_labels is not None:
        quality_labels.validate_dataset(dataset)
        fingerprints["quality_labels_sha256"] = fingerprint(
            quality_labels.model_dump_json().encode("utf-8")
        )
    measured_at = datetime.now(UTC).isoformat()
    observations: list[Observation] = []
    for case in dataset.cases:
        for repetition in range(1, config.repetitions + 1):
            observations.extend(
                _pair(config, case, repetition, transport, quality_labels)
            )
    configuration = asdict(config)
    configuration["as_of"] = config.as_of.isoformat()
    rubric = load_scoring_rubric_v2(ROOT / "config/scoring_rubric.toml")
    return BenchmarkReport(
        "analysis-benchmark-v2" if quality_labels else _SCHEMA,
        measured_at,
        "live_provider" if config.live else "fixture",
        "application_cache_cold_warm_with_fixture_retrieval",
        configuration,
        source,
        {"python": platform.python_version(), "platform": platform.system()},
        fingerprints,
        {
            "chunking": CHUNKING_PROMPT_VERSION,
            "judge": JUDGE_PROMPT_VERSION,
            "judge_anchors": JUDGE_ANCHOR_VERSION,
            "cv_contract": CvChunkResponse.contract_version,
            "job_contract": JobChunkResponse.contract_version,
            "judge_contract": JudgeResponse.contract_version,
            "rubric": rubric.version,
        },
        tuple(observations),
        _summaries(observations),
        _quality_summary(quality_labels, observations) if quality_labels else None,
    )


def _quality_summary(
    labels: QualityLabels, observations: Sequence[Observation]
) -> dict[str, object]:
    groups: dict[tuple[int, Temperature], dict[str, float | None]] = {}
    for item in observations:
        scores = groups.setdefault((item.repetition, item.temperature), {})
        scores[item.case_id] = item.score if item.status == SUCCEEDED else None
    return {
        "label_version": labels.version,
        "basis": labels.basis,
        "ranking_groups": [
            {
                "repetition": repetition,
                "temperature": temperature,
                **ranking_agreement(labels.rankings, scores),
            }
            for (repetition, temperature), scores in groups.items()
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--as-of", default="2026-09-01")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--quality", action="store_true")
    parser.add_argument(
        "--provider",
        choices=("hermetic", "ollama", "openai", "anthropic"),
        default="hermetic",
    )
    parser.add_argument(
        "--embedding-provider", choices=("hermetic", "ollama", "openai")
    )
    parser.add_argument("--completion-model")
    parser.add_argument("--embedding-model")
    return parser


def _config(arguments: argparse.Namespace) -> BenchmarkConfig:
    embedding = arguments.embedding_provider or (
        "ollama" if arguments.live else "hermetic"
    )
    return BenchmarkConfig(
        repetitions=arguments.repetitions,
        as_of=date.fromisoformat(arguments.as_of),
        live=arguments.live,
        provider=arguments.provider,
        embedding_provider=embedding,
        completion_model=arguments.completion_model,
        embedding_model=arguments.embedding_model,
    )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    output: TextIO | None = None
    try:
        config = _config(arguments)
        selected = arguments.case or (QUALITY_CASES if arguments.quality else ())
        dataset = load_dataset(selected)
        quality_labels = None
        label_hash = None
        if arguments.quality:
            quality_labels, label_hash = load_quality(dataset)
        if arguments.output is not None:
            # Reserve before any paid work, and never overwrite an existing artifact.
            output = arguments.output.open("x", encoding="utf-8")
        report = run_benchmark(config, dataset, quality_labels=quality_labels)
        if label_hash is not None:
            report.fingerprints["quality_label_file_sha256"] = label_hash
        target = output or sys.stdout
        json.dump(report.payload(), target, indent=2, allow_nan=False)
        target.write("\n")
        return 0 if report.succeeded else 1
    except OSError, ValueError:
        print("benchmark_invalid_arguments_or_output", file=sys.stderr)
        return 2
    finally:
        if output is not None:
            output.close()


if __name__ == "__main__":
    raise SystemExit(main())
