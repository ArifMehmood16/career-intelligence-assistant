"""The digest of the weights a local Ollama tag points at (ADR 014).

A tag can be re-pulled to different weights, so the verdict cache keys on this.
Any failure reports no digest: the cost is a cache miss, never a wrong reuse.
"""

from __future__ import annotations

import json

from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.providers.resilience import classify_http_status
from career_assistant.application.ports.errors import ProviderError

_LATEST = ":latest"


def ollama_model_digest(
    transport: HttpTransport,
    *,
    base_url: str,
    model_tag: str,
    timeout_seconds: float,
) -> str | None:
    try:
        response = transport.request(
            "GET",
            f"{base_url.rstrip('/')}/api/tags",
            timeout_seconds=timeout_seconds,
        )
        classify_http_status(response.status_code)
        data = json.loads(response.body.decode("utf-8"))
    except ProviderError, ValueError:
        return None
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return None
    wanted = model_tag if ":" in model_tag else f"{model_tag}{_LATEST}"
    for model in models:
        if isinstance(model, dict) and model.get("name") == wanted:
            digest = model.get("digest")
            return digest if isinstance(digest, str) and digest else None
    return None
