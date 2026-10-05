"""Stable ids for server-owned document citations."""

from __future__ import annotations

import uuid

_SPAN_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def span_id(document_id: str, start: int, end: int) -> str:
    """Deterministic UUID for a server-owned (document, offset) span."""
    return str(uuid.uuid5(_SPAN_NAMESPACE, f"{document_id}:{start}:{end}"))
