"""Hermetic embeddings — lexical hashing, fixed dimensions, no network."""

from __future__ import annotations

import hashlib
import math
import re

from career_assistant.application.ports.errors import ProviderInputTooLargeError
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    EmbeddingRequest,
    EmbeddingResult,
)

_TOKEN = re.compile(r"[a-z0-9]+")
_DIMENSIONS = 64
_CONTEXT = 8_192


class HermeticEmbeddingAdapter:
    provider_id = "hermetic"
    model_tag = "lexical-hash-v1"

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id=self.provider_id,
            supports_completion=False,
            supports_embedding=True,
            supports_structured_output=False,
            context_window_tokens=_CONTEXT,
            max_output_tokens=0,
            embedding_dimensions=_DIMENSIONS,
            leaves_machine=False,
        )

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        vectors: list[tuple[float, ...]] = []
        for text in request.texts:
            if len(text) > request.max_chars_per_text:
                raise ProviderInputTooLargeError(
                    f"text of {len(text)} characters exceeds "
                    f"max_chars_per_text={request.max_chars_per_text}"
                )
            vectors.append(_hash_embed(text, _DIMENSIONS))

        return EmbeddingResult(
            vectors=tuple(vectors),
            provider_id=self.provider_id,
            model_tag=self.model_tag,
            dimensions=_DIMENSIONS,
            left_machine=False,
            input_tokens=sum(max(1, len(t.split())) for t in request.texts),
            latency_ms=0,
        )


def _hash_embed(text: str, dimensions: int) -> tuple[float, ...]:
    counts = [0.0] * dimensions
    for token in _TOKEN.findall(text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        counts[index] += sign
    norm = math.sqrt(sum(v * v for v in counts)) or 1.0
    return tuple(v / norm for v in counts)
