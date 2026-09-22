"""Embedding rows come back as numeric arrays, including numpy vectors."""

from __future__ import annotations

import pytest

from career_assistant.adapters.persistence.embedding_repos import _as_vector


def test_embedding_vector_accepts_a_numpy_array() -> None:
    numpy = pytest.importorskip("numpy")
    vector = numpy.zeros(4, dtype=numpy.float32)
    vector[-1] = 1
    assert _as_vector(vector) == (0.0, 0.0, 0.0, 1.0)
