"""Three-signal relatedness — pure combination, no I/O."""

from __future__ import annotations

import re
from dataclasses import dataclass

from career_assistant.domain.claims import Claim
from career_assistant.domain.requirements import Requirement

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "for",
        "with",
        "on",
        "in",
        "of",
        "to",
        "by",
        "at",
        "from",
        "experience",
        "strong",
        "production",
        "owned",
        "wrote",
        "built",
        "used",
    }
)


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


def lexical_tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 2}


def lexical_overlap(left: str, right: str) -> int:
    return len(lexical_tokens(left) & lexical_tokens(right))


def combine_relatedness(
    *,
    lexical: bool,
    lexical_overlap: int,
    embedding: bool,
    embedding_similarity: float,
    adjudication: bool | None,
) -> RelatednessSignals:
    """Combine the three signals.

    Agreement of lexical and embedding is final — adjudication is not asked and
    is ignored if somehow present. Disagreement is a tie-break: the adjudicator
    decides when it answered, otherwise hermetic analysis falls back to OR so
    an embedding-only candidate is not silently dropped.
    """
    if lexical == embedding:
        related = lexical
        used_adjudication = None
    elif adjudication is None:
        related = lexical or embedding
        used_adjudication = None
    else:
        related = adjudication
        used_adjudication = adjudication
    return RelatednessSignals(
        lexical=lexical,
        lexical_overlap=lexical_overlap,
        embedding=embedding,
        embedding_similarity=embedding_similarity,
        adjudication=used_adjudication,
        related=related,
    )


def pair_relatedness(
    requirement: Requirement,
    claim: Claim,
    *,
    similarity: float,
    similarity_floor: float,
    adjudication: bool | None,
) -> RelatednessSignals:
    overlap = lexical_overlap(requirement.text, claim.context)
    return combine_relatedness(
        lexical=overlap >= 1,
        lexical_overlap=overlap,
        embedding=similarity >= similarity_floor,
        embedding_similarity=similarity,
        adjudication=adjudication,
    )
