"""Load the fit-score rubric and mapping floor from configuration."""

from __future__ import annotations

import tomllib
from pathlib import Path

from career_assistant.domain.scoring_v2 import RubricV2


def load_scoring_rubric_v2(path: Path | str) -> RubricV2:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))["v2"]
    dimensions = data["dimension_weights"]
    weights = data["weights"]
    recency = data["recency"]
    bands = data["bands"]
    return RubricV2(
        version=str(data["version"]),
        w_match=float(dimensions["match"]),
        w_experience=float(dimensions["experience"]),
        w_seniority=float(dimensions["seniority"]),
        weight_must_have=float(weights["must_have"]),
        weight_desirable=float(weights["desirable"]),
        recency_recent=float(recency["within_2y"]),
        recency_mid=float(recency["from_2y_to_5y"]),
        recency_old=float(recency["over_5y"]),
        recency_undated=float(recency["undated"]),
        band_strong_min=float(bands["strong_match_min"]),
        band_partial_min=float(bands["partial_match_min"]),
        gate_match_max=int(data["gate"]["must_have_match_max"]),
    )
