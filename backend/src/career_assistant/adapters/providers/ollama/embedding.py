"""Ollama embedding adapter."""

from __future__ import annotations

import json

from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.providers.resilience import (
    ResiliencePolicy,
    classify_http_status,
)
from career_assistant.application.ports.errors import (
    ProviderInputTooLargeError,
    ProviderUnavailableError,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    EmbeddingRequest,
    EmbeddingResult,
)


class OllamaEmbeddingAdapter:
    provider_id = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model_tag: str,
        transport: HttpTransport,
        resilience: ResiliencePolicy,
        dimensions: int = 768,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_tag = model_tag
        self._transport = transport
        self._resilience = resilience
        self._dimensions = dimensions

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id=self.provider_id,
            supports_completion=False,
            supports_embedding=True,
            supports_structured_output=False,
            context_window_tokens=8_192,
            max_output_tokens=0,
            embedding_dimensions=self._dimensions,
            leaves_machine=False,
        )

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        vectors: list[tuple[float, ...]] = []
        for text in request.texts:
            if len(text) > request.max_chars_per_text:
                raise ProviderInputTooLargeError("ollama embedding input too large")

            def _call(current: str = text) -> tuple[float, ...]:
                response = self._transport.request(
                    "POST",
                    f"{self._base_url}/api/embeddings",
                    json_body={"model": self._model_tag, "prompt": current},
                    timeout_seconds=self._resilience.timeout_seconds,
                )
                classify_http_status(response.status_code)
                data = json.loads(response.body.decode("utf-8"))
                raw = data.get("embedding")
                if not isinstance(raw, list):
                    raise ProviderUnavailableError("ollama returned no embedding")
                return tuple(float(x) for x in raw)

            vectors.append(self._resilience.run(_call))

        dims = len(vectors[0]) if vectors else self._dimensions
        return EmbeddingResult(
            vectors=tuple(vectors),
            provider_id=self.provider_id,
            model_tag=self._model_tag,
            dimensions=dims,
            left_machine=False,
            input_tokens=None,
        )
