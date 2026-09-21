"""Pure cosine similarity — no I/O."""

from __future__ import annotations

import pytest

from career_assistant.domain.similarity import cosine_similarity


def test_identical_unit_vectors_are_one() -> None:
    vector = (1.0, 0.0, 0.0)
    assert cosine_similarity(vector, vector) == pytest.approx(1.0)


def test_orthogonal_vectors_are_zero() -> None:
    assert cosine_similarity((1.0, 0.0), (0.0, 1.0)) == pytest.approx(0.0)


def test_zero_vector_is_zero_similarity() -> None:
    assert cosine_similarity((0.0, 0.0), (1.0, 0.0)) == 0.0


def test_mismatched_dimensions_raise() -> None:
    with pytest.raises(ValueError, match="dimension"):
        cosine_similarity((1.0, 0.0), (1.0, 0.0, 0.0))
