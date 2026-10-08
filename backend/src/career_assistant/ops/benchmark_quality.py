"""Frozen development labels for the current judge, never citation-as-support claims."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from career_assistant.domain.judging import VerdictLabel
from career_assistant.ops.benchmark_cases import ROOT, BenchmarkDataset, fingerprint

QUALITY_CASES = ("partial_match", "poor_match")


class RequirementLabel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    quote: str = Field(min_length=1)
    expected: VerdictLabel


class CaseLabels(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    case_id: str
    cv_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    jd_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    requirements: tuple[RequirementLabel, ...] = Field(min_length=1)


class RankingLabel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    higher: str
    lower: str


class QualityLabels(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal["current-judge-development-v1"]
    basis: str
    cases: tuple[CaseLabels, ...] = Field(min_length=1)
    rankings: tuple[RankingLabel, ...]

    def validate_dataset(self, dataset: BenchmarkDataset) -> None:
        cases = {item.case_id: item for item in self.cases}
        if len(cases) != len(self.cases):
            raise ValueError("duplicate_label_case")
        for case in dataset.cases:
            label = cases.get(case.case_id)
            if label is None or (label.cv_sha256, label.jd_sha256) != (
                case.cv_sha256,
                case.jd_sha256,
            ):
                raise ValueError("quality_fixture_fingerprint_mismatch")
        for label in self.cases:
            quotes = [normalize(item.quote) for item in label.requirements]
            if len(set(quotes)) != len(quotes):
                raise ValueError("duplicate_requirement_label")
        for ranking in self.rankings:
            high, low = cases.get(ranking.higher), cases.get(ranking.lower)
            if (
                high is None
                or low is None
                or high.case_id == low.case_id
                or high.cv_sha256 != low.cv_sha256
            ):
                raise ValueError("ranking_requires_distinct_jobs_for_same_cv")


def load_quality(dataset: BenchmarkDataset) -> tuple[QualityLabels, str]:
    raw = (ROOT / "sample-data/evaluation/current-judge-labels.json").read_bytes()
    labels = QualityLabels.model_validate_json(raw)
    labels.validate_dataset(dataset)
    return labels, fingerprint(raw)


def normalize(quote: str) -> str:
    # Preserve punctuation such as C++; only presentation whitespace/case changes.
    return " ".join(quote.strip().removeprefix("- ").rstrip(".").split()).casefold()


@dataclass(frozen=True, slots=True)
class JudgedLabel:
    quote: str
    verdict: VerdictLabel | None


@dataclass(frozen=True, slots=True)
class QualityMetrics:
    expected_requirements: int
    matched_requirements: int
    correct_labels: int
    unmatched_requirements: int
    unlabelled_requirements: int
    duplicate_requirements: int
    missing_verdicts: int
    predicted_met: int
    labelled_met: int
    unsupported_met: int
    label_agreement: float
    unsupported_met_rate: float | None


def measure(labels: CaseLabels, judgments: Sequence[JudgedLabel]) -> QualityMetrics:
    grouped: dict[str, list[VerdictLabel | None]] = {}
    for item in judgments:
        grouped.setdefault(normalize(item.quote), []).append(item.verdict)
    expected = {normalize(item.quote): item.expected for item in labels.requirements}
    matched = sum(quote in grouped for quote in expected)
    correct = sum(grouped.get(quote) == [value] for quote, value in expected.items())
    labelled_met = sum(
        values.count("met") for quote, values in grouped.items() if quote in expected
    )
    unsupported = sum(
        values.count("met")
        for quote, values in grouped.items()
        if quote in expected and expected[quote] != "met"
    )
    return QualityMetrics(
        expected_requirements=len(expected),
        matched_requirements=matched,
        correct_labels=correct,
        unmatched_requirements=len(expected) - matched,
        unlabelled_requirements=sum(
            len(values) for quote, values in grouped.items() if quote not in expected
        ),
        duplicate_requirements=sum(len(values) - 1 for values in grouped.values()),
        missing_verdicts=sum(item.verdict is None for item in judgments),
        predicted_met=sum(item.verdict == "met" for item in judgments),
        labelled_met=labelled_met,
        unsupported_met=unsupported,
        label_agreement=correct / len(expected),
        unsupported_met_rate=unsupported / labelled_met if labelled_met else None,
    )


def ranking_agreement(
    labels: Sequence[RankingLabel], scores: Mapping[str, float | None]
) -> dict[str, int | float | None]:
    eligible = agreed = 0
    for label in labels:
        high, low = scores.get(label.higher), scores.get(label.lower)
        if high is None or low is None:
            continue
        eligible += 1
        agreed += high > low
    return {
        "expected_pairs": len(labels),
        "eligible_pairs": eligible,
        "agreed_pairs": agreed,
        "agreement": agreed / eligible if eligible else None,
    }
