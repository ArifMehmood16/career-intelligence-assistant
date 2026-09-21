"""Load the fit-score rubric and mapping floor from configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from career_assistant.domain.scoring import ScoringRubric


@dataclass(frozen=True, slots=True)
class MappingConfig:
    similarity_floor: float


def load_mapping_config(path: Path | str) -> MappingConfig:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    mapping = data["mapping"]
    return MappingConfig(similarity_floor=float(mapping["similarity_floor"]))


def load_scoring_rubric(path: Path | str) -> ScoringRubric:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    weights = data["weights"]
    status = data["status"]
    recency = data["recency"]
    bands = data["bands"]
    return ScoringRubric(
        weight_must_have=float(weights["must_have"]),
        weight_desirable=float(weights["desirable"]),
        status_met=float(status["met"]),
        status_partial=float(status["partial"]),
        status_missing=float(status["missing"]),
        recency_recent=float(recency["within_2y"]),
        recency_mid=float(recency["from_2y_to_5y"]),
        recency_old=float(recency["over_5y"]),
        band_strong_min=float(bands["strong_match_min"]),
        band_partial_min=float(bands["partial_match_min"]),
    )
