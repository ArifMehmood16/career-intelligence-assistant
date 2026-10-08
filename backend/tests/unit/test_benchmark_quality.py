"""Current-label agreement is conservative about extraction and failed scoring."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from career_assistant.ops.benchmark import main, run_benchmark
from career_assistant.ops.benchmark_cases import load_dataset
from career_assistant.ops.benchmark_quality import (
    JudgedLabel,
    load_quality,
    measure,
    ranking_agreement,
)
from career_assistant.ops.benchmark_runtime import BenchmarkConfig


def test_unsupported_met_and_unmatched_labels_are_not_dropped() -> None:
    labels, _ = load_quality(load_dataset(["partial_match", "poor_match"]))
    case = labels.cases[0]
    first, second, third = case.requirements[:3]
    metric = measure(
        case,
        (
            JudgedLabel(first.quote, "met"),
            JudgedLabel(second.quote, "partial"),
            JudgedLabel(third.quote, None),
            JudgedLabel("An invented requirement", "met"),
        ),
    )
    assert metric.expected_requirements == 6
    assert metric.matched_requirements == 3
    assert metric.correct_labels == 1
    assert metric.unmatched_requirements == 3
    assert metric.unlabelled_requirements == 1
    assert metric.missing_verdicts == 1
    assert metric.predicted_met == 2
    assert metric.unsupported_met == 1
    assert metric.label_agreement == pytest.approx(1 / 6)
    assert metric.labelled_met == 1
    assert metric.unsupported_met_rate == 1.0


def test_duplicate_extraction_does_not_inflate_agreement() -> None:
    labels, _ = load_quality(load_dataset(["poor_match"]))
    case = labels.cases[1]
    metric = measure(
        case,
        (
            JudgedLabel(case.requirements[0].quote, "missing"),
            JudgedLabel(case.requirements[0].quote, "missing"),
        ),
    )
    assert metric.duplicate_requirements == 1
    assert metric.correct_labels == 0
    assert metric.unmatched_requirements == 4
    assert metric.unsupported_met_rate is None


def test_ranking_uses_same_cv_and_excludes_failed_scores() -> None:
    labels, _ = load_quality(load_dataset(["partial_match", "poor_match"]))
    scores = {"partial_match": 30.0, "poor_match": 0.0}
    assert ranking_agreement(labels.rankings, scores) == {
        "expected_pairs": 1,
        "eligible_pairs": 1,
        "agreed_pairs": 1,
        "agreement": 1.0,
    }
    assert (
        ranking_agreement(labels.rankings, {"partial_match": 0.0, "poor_match": 0.0})[
            "agreement"
        ]
        == 0.0
    )
    assert (
        ranking_agreement(labels.rankings, {"partial_match": None, "poor_match": 0.0})[
            "agreement"
        ]
        is None
    )


def test_changed_fixture_is_rejected_before_any_model_work() -> None:
    dataset = load_dataset(["poor_match"])
    changed = replace(dataset.cases[0], jd_sha256="0" * 64)
    with pytest.raises(ValueError, match="fingerprint_mismatch"):
        load_quality(replace(dataset, cases=(changed,)))


def test_quality_command_records_safe_metrics_with_no_default_schema_change(
    tmp_path: Path,
) -> None:
    output = tmp_path / "quality.json"
    assert main(["--quality", "--output", str(output)]) == 0
    payload = json.loads(output.read_text())
    assert payload["schema_version"] == "analysis-benchmark-v2"
    assert payload["fingerprints"]["quality_labels_sha256"]
    assert len(payload["observations"]) == 4
    assert payload["quality"]["ranking_groups"][0]["eligible_pairs"] == 1
    for observation in payload["observations"]:
        assert observation["quality"]["expected_requirements"] in {5, 6}
        assert observation["quality"]["unmatched_requirements"] == 0
        assert observation["counts"]["physical_attempts"] == {
            "completion": 0,
            "embedding": 0,
            "metadata": 0,
        }
    assert "Hands-on dbt" not in output.read_text()
    ordinary = run_benchmark(BenchmarkConfig(), load_dataset(["poor_match"])).payload()
    assert ordinary["schema_version"] == "analysis-benchmark-v1"
    assert "quality" not in ordinary
    assert "quality" not in ordinary["observations"][0]


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("duplicate_case", "duplicate_label_case"),
        ("duplicate_quote", "duplicate_requirement_label"),
        ("invented_quote", "quality_label_quote_not_in_fixture"),
        ("different_cv", "ranking_requires_distinct_jobs_for_same_cv"),
        ("same_job", "ranking_requires_distinct_jobs_for_same_cv"),
        ("unknown_job", "ranking_requires_distinct_jobs_for_same_cv"),
    ],
)
def test_invalid_label_sets_are_rejected(mutation: str, code: str) -> None:
    dataset = load_dataset(["partial_match"])
    labels, _ = load_quality(dataset)
    first, second = labels.cases
    if mutation == "duplicate_case":
        labels = labels.model_copy(update={"cases": (first, first)})
    elif mutation == "duplicate_quote":
        first = first.model_copy(
            update={"requirements": (first.requirements[0], first.requirements[0])}
        )
        labels = labels.model_copy(update={"cases": (first, second)})
    elif mutation == "invented_quote":
        requirement = first.requirements[0].model_copy(
            update={"quote": "An invented requirement"}
        )
        first = first.model_copy(update={"requirements": (requirement,)})
        labels = labels.model_copy(update={"cases": (first, second)})
    elif mutation == "different_cv":
        second = second.model_copy(update={"cv_sha256": "0" * 64})
        labels = labels.model_copy(update={"cases": (first, second)})
    else:
        lower = "partial_match" if mutation == "same_job" else "unknown"
        rank = labels.rankings[0].model_copy(update={"lower": lower})
        labels = labels.model_copy(update={"rankings": (rank,)})
    with pytest.raises(ValueError, match=code):
        run_benchmark(BenchmarkConfig(), dataset, quality_labels=labels)
