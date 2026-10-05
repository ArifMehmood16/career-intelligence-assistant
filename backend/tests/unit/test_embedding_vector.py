"""The current chunk-vector adapter accepts numeric arrays without truth tests."""

from __future__ import annotations

import uuid
from unittest.mock import Mock

import numpy

from career_assistant.adapters.persistence.chunk_repos import SqlChunkRepository
from career_assistant.application.ports.chunks import ChunkVector, EmbeddingModel


def test_chunk_vector_storage_accepts_a_numpy_array() -> None:
    vector = numpy.zeros(4, dtype=numpy.float32)
    vector[-1] = 1
    session = Mock()
    model = EmbeddingModel("test", "embed", 4, "document")

    SqlChunkRepository(session).save_vectors(
        str(uuid.uuid4()), model, (ChunkVector(str(uuid.uuid4()), vector),)
    )

    rows = list(session.add_all.call_args.args[0])
    assert len(rows) == 1
    assert rows[0].embedding == [0.0, 0.0, 0.0, 1.0]
    assert rows[0].model_key == model.key
    session.flush.assert_called_once()
