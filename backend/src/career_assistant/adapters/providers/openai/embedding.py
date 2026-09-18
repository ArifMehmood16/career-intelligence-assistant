"""OpenAI embeddings adapter — hosted; construct only via egress gate."""

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


class OpenAIEmbeddingAdapter:
    provider_id = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model_tag: str,
        transport: HttpTransport,
        resilience: ResiliencePolicy,
        dimensions: int = 1536,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self._api_key = api_key
        self._model_tag = model_tag
        self._transport = transport
        self._resilience = resilience
        self._dimensions = dimensions
        self._base_url = base_url.rstrip("/")

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
            leaves_machine=True,
        )

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        for text in request.texts:
            if len(text) > request.max_chars_per_text:
                raise ProviderInputTooLargeError("openai embedding input too large")

        def _call() -> EmbeddingResult:
            response = self._transport.request(
                "POST",
                f"{self._base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json_body={
                    "model": self._model_tag,
                    "input": list(request.texts),
                },
                timeout_seconds=self._resilience.timeout_seconds,
            )
            classify_http_status(response.status_code)
            data = json.loads(response.body.decode("utf-8"))
            items = data.get("data")
            if not isinstance(items, list):
                raise ProviderUnavailableError("openai returned no embeddings")
            vectors = tuple(
                tuple(float(x) for x in item["embedding"]) for item in items
            )
            dims = len(vectors[0]) if vectors else self._dimensions
            usage = data.get("usage") or {}
            return EmbeddingResult(
                vectors=vectors,
                provider_id=self.provider_id,
                model_tag=self._model_tag,
                dimensions=dims,
                left_machine=True,
                input_tokens=usage.get("total_tokens")
                if isinstance(usage.get("total_tokens"), int)
                else None,
            )

        return self._resilience.run(_call)
