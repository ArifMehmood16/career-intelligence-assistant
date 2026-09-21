"""Vector similarity — pure functions, no I/O."""

from __future__ import annotations

import math
from collections.abc import Sequence


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Exact cosine over two vectors. Zero vectors score 0.0."""
    if len(left) != len(right):
        raise ValueError(
            f"cosine similarity requires equal dimensions, "
            f"got {len(left)} and {len(right)}"
        )
    if not left:
        return 0.0
    dot = 0.0
    left_norm_sq = 0.0
    right_norm_sq = 0.0
    for a, b in zip(left, right, strict=True):
        dot += a * b
        left_norm_sq += a * a
        right_norm_sq += b * b
    if left_norm_sq == 0.0 or right_norm_sq == 0.0:
        return 0.0
    return dot / math.sqrt(left_norm_sq * right_norm_sq)
