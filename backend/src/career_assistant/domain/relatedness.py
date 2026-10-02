"""Optional diagnostic values carried by analysis presentation contracts."""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class RelatednessSignals:
    lexical: bool = False
    lexical_overlap: int = 0
    embedding: bool = False
    embedding_similarity: float = 0.0
    adjudication: bool | None = None
    related: bool = False

    def as_payload(self) -> dict[str, bool | int | float | None]:
        return {
            "lexical": self.lexical,
            "lexical_overlap": self.lexical_overlap,
            "embedding": self.embedding,
            "embedding_similarity": self.embedding_similarity,
            "adjudication": self.adjudication,
            "related": self.related,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object] | None) -> RelatednessSignals:
        if not payload:
            return cls()
        adjudication_raw = payload.get("adjudication")
        adjudication: bool | None
        if adjudication_raw is True:
            adjudication = True
        elif adjudication_raw is False:
            adjudication = False
        else:
            adjudication = None
        return cls(
            lexical=bool(payload.get("lexical", False)),
            lexical_overlap=_as_int(payload.get("lexical_overlap")),
            embedding=bool(payload.get("embedding", False)),
            embedding_similarity=_as_float(payload.get("embedding_similarity")),
            adjudication=adjudication,
            related=bool(payload.get("related", False)),
        )


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def _as_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0
    return float(value)
