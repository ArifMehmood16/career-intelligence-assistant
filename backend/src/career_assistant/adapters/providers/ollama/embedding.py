"""Ollama embedding adapter."""

from __future__ import annotations

import json
import math

from career_assistant.adapters.providers.execution import execution_profile
from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.providers.local_gate import local_call_slot
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
    ModelProfile,
)

# The v1 constants, used when no catalogue profile is passed (tests, old callers).
_DEFAULT_PROFILE = ModelProfile(context_window_tokens=8_192, max_output_tokens=0)


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
        profile: ModelProfile | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_tag = model_tag
        self._transport = transport
        self._resilience = resilience
        self._dimensions = dimensions
        self._profile = profile or _DEFAULT_PROFILE

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id=self.provider_id,
            model_tag=self._model_tag,
            supports_completion=False,
            supports_embedding=True,
            supports_structured_output=False,
            context_window_tokens=self._profile.context_window_tokens,
            max_output_tokens=0,
            embedding_dimensions=self._dimensions,
            leaves_machine=False,
            execution=execution_profile(self._profile),
            supports_tool_calling=self._profile.supports_tool_calling,
            supports_prompt_caching=self._profile.supports_prompt_caching,
            supports_temperature=self._profile.supports_temperature,
            supports_seed=self._profile.supports_seed,
        )

    def _prefixed(self, text: str, request: EmbeddingRequest) -> str:
        if request.input_type == "query":
            return f"{self._profile.embedding_query_prefix}{text}"
        if request.input_type == "document":
            return f"{self._profile.embedding_document_prefix}{text}"
        return text

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        for text in request.texts:
            if len(text) > request.max_chars_per_text:
                raise ProviderInputTooLargeError("ollama embedding input too large")
        if not request.texts:
            return EmbeddingResult(
                vectors=(),
                provider_id=self.provider_id,
                model_tag=self._model_tag,
                dimensions=self._dimensions,
                left_machine=False,
            )

        def call() -> EmbeddingResult:
            response = self._transport.request(
                "POST",
                f"{self._base_url}/api/embed",
                json_body={
                    "model": self._model_tag,
                    "input": [self._prefixed(text, request) for text in request.texts],
                    "truncate": False,
                    "options": {"num_ctx": self._profile.context_window_tokens},
                },
                timeout_seconds=self._resilience.timeout_seconds,
            )
            classify_http_status(response.status_code, response.headers)
            try:
                data = json.loads(response.body.decode("utf-8"))
                vectors = _parse_vectors(data.get("embeddings"), len(request.texts))
            except (UnicodeDecodeError, ValueError, TypeError, AttributeError) as exc:
                raise ProviderUnavailableError(
                    "ollama returned invalid embeddings"
                ) from exc
            tokens = data.get("prompt_eval_count")
            return EmbeddingResult(
                vectors=vectors,
                provider_id=self.provider_id,
                model_tag=self._model_tag,
                dimensions=len(vectors[0]),
                left_machine=False,
                input_tokens=tokens if isinstance(tokens, int) else None,
            )

        with local_call_slot(
            self.provider_id,
            self._model_tag,
            operation="embedding",
            max_in_flight=self._profile.embedding_concurrency,
        ):
            return self._resilience.run(call)


def _parse_vectors(raw: object, count: int) -> tuple[tuple[float, ...], ...]:
    if not isinstance(raw, list) or len(raw) != count:
        raise ValueError("embedding count mismatch")
    vectors: list[tuple[float, ...]] = []
    for item in raw:
        if not isinstance(item, list) or not item:
            raise ValueError("empty embedding")
        if any(type(value) not in (int, float) for value in item):
            raise ValueError("non-numeric embedding")
        vector = tuple(float(value) for value in item)
        if any(not math.isfinite(value) for value in vector):
            raise ValueError("non-finite embedding")
        if vectors and len(vector) != len(vectors[0]):
            raise ValueError("embedding dimensions mismatch")
        vectors.append(vector)
    return tuple(vectors)
