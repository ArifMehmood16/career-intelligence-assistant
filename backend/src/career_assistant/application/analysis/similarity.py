"""Requirement-claim embedding similarities for mapping candidates."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field

from career_assistant.application.ports.embedding import (
    EmbeddingCachePort,
    EmbeddingPort,
)
from career_assistant.application.ports.types import EmbeddingRequest
from career_assistant.domain.claims import Claim
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.similarity import cosine_similarity

_DEFAULT_MAX_CHARS = 12_000
_OWNER_REQUIREMENT = "requirement"
_OWNER_CLAIM = "claim"


@dataclass
class InMemoryEmbeddingCache:
    """Process-local cache — tests and hermetic analysis, not a store of record."""

    _items: dict[tuple[str, str, str, str, str, str], tuple[float, ...]] = field(
        default_factory=dict
    )

    def get(
        self,
        workspace_id: str,
        *,
        owner_kind: str,
        owner_id: str,
        provider: str,
        model_tag: str,
        text_sha256: str,
    ) -> tuple[float, ...] | None:
        return self._items.get(
            (workspace_id, owner_kind, owner_id, provider, model_tag, text_sha256)
        )

    def put(
        self,
        workspace_id: str,
        *,
        owner_kind: str,
        owner_id: str,
        provider: str,
        model_tag: str,
        text_sha256: str,
        dimensions: int,
        vector: tuple[float, ...],
    ) -> None:
        if dimensions != len(vector):
            return
        self._items[
            (workspace_id, owner_kind, owner_id, provider, model_tag, text_sha256)
        ] = vector


def requirement_claim_similarities(
    *,
    workspace_id: str,
    requirements: Sequence[Requirement],
    claims: Sequence[Claim],
    embedding: EmbeddingPort | None,
    cache: EmbeddingCachePort | None,
    provider_id: str,
    model_tag: str,
    max_chars_per_text: int = _DEFAULT_MAX_CHARS,
) -> dict[tuple[str, str], float]:
    """Return pair cosine scores, or {} when embeddings cannot run."""
    if embedding is None or not requirements or not claims:
        return {}

    owners: list[tuple[str, str, str]] = [
        (_OWNER_REQUIREMENT, req.id, req.text) for req in requirements
    ]
    owners.extend((_OWNER_CLAIM, claim.id, claim.context) for claim in claims)

    resolved_cache = cache or InMemoryEmbeddingCache()
    vectors: dict[tuple[str, str], tuple[float, ...]] = {}
    missing: list[tuple[str, str, str, str]] = []
    cached_dim: int | None = None

    for owner_kind, owner_id, text in owners:
        digest = _sha256(text)
        found = resolved_cache.get(
            workspace_id,
            owner_kind=owner_kind,
            owner_id=owner_id,
            provider=provider_id,
            model_tag=model_tag,
            text_sha256=digest,
        )
        if found is None:
            missing.append((owner_kind, owner_id, text, digest))
            continue
        if cached_dim is None:
            cached_dim = len(found)
        elif len(found) != cached_dim:
            return {}
        vectors[(owner_kind, owner_id)] = found

    if missing:
        unique_texts: list[str] = []
        seen: set[str] = set()
        for _kind, _oid, text, _digest in missing:
            if text in seen:
                continue
            seen.add(text)
            unique_texts.append(text)
        try:
            result = embedding.embed(
                EmbeddingRequest(
                    texts=tuple(unique_texts),
                    max_chars_per_text=max_chars_per_text,
                )
            )
        except Exception:
            return {}
        if len(result.vectors) != len(unique_texts):
            return {}
        new_dim = result.dimensions
        if any(len(vector) != new_dim for vector in result.vectors):
            return {}
        if cached_dim is not None and cached_dim != new_dim:
            return {}
        by_text = dict(zip(unique_texts, result.vectors, strict=True))
        for owner_kind, owner_id, text, digest in missing:
            vector = by_text[text]
            vectors[(owner_kind, owner_id)] = vector
            resolved_cache.put(
                workspace_id,
                owner_kind=owner_kind,
                owner_id=owner_id,
                provider=provider_id,
                model_tag=model_tag,
                text_sha256=digest,
                dimensions=new_dim,
                vector=vector,
            )

    scores: dict[tuple[str, str], float] = {}
    for req in requirements:
        left = vectors.get((_OWNER_REQUIREMENT, req.id))
        if left is None:
            continue
        for claim in claims:
            right = vectors.get((_OWNER_CLAIM, claim.id))
            if right is None:
                continue
            try:
                scores[(req.id, claim.id)] = cosine_similarity(left, right)
            except ValueError:
                return {}
    return scores


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
