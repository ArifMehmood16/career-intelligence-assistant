"""Groundedness validator — drafts may only assert tokens present in cited spans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from career_assistant.domain.normalisation import normalise_text

# Product/technology tokens that must be span-backed when used in a draft.
_TECH = frozenset(
    {
        "dbt",
        "snowflake",
        "airflow",
        "spark",
        "kubernetes",
        "k8s",
        "python",
        "sql",
        "looker",
        "bigquery",
        "redshift",
        "kafka",
        "hadoop",
        "terraform",
        "docker",
        "aws",
        "gcp",
        "azure",
        "cuda",
        "ros2",
        "pytorch",
        "tensorflow",
    }
)

_PERCENT = re.compile(r"\b\d+(?:\.\d+)?%")
_NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")
_DURATION = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:years?|months?|weeks?|days?)\b",
    re.IGNORECASE,
)
_PROPER = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+.#/-]*")

_STOP_PROPER = frozenset(
    {
        "Led",
        "Built",
        "Owned",
        "Used",
        "Reduced",
        "Shipped",
        "Worked",
        "The",
        "For",
        "And",
        "With",
    }
)


class GroundednessVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class GroundednessResult:
    verdict: GroundednessVerdict
    ungrounded_tokens: tuple[str, ...]


def validate_groundedness(
    draft: str,
    spans: tuple[str, ...] | list[str],
) -> GroundednessResult:
    """Assert every sensitive draft token appears in the cited span text."""
    text = draft.strip()
    if not text:
        return GroundednessResult(
            verdict=GroundednessVerdict.PASS, ungrounded_tokens=()
        )

    corpus = normalise_text("\n".join(spans)).lower()
    tokens = _extract_tokens(text)
    ungrounded: list[str] = []
    for token in tokens:
        if not _token_in_corpus(token, corpus):
            ungrounded.append(token)
    if ungrounded:
        return GroundednessResult(
            verdict=GroundednessVerdict.FAIL,
            ungrounded_tokens=tuple(ungrounded),
        )
    return GroundednessResult(verdict=GroundednessVerdict.PASS, ungrounded_tokens=())


def _extract_tokens(draft: str) -> tuple[str, ...]:
    found: list[str] = []
    seen: set[str] = set()

    def add(token: str) -> None:
        key = token.lower()
        if key not in seen:
            seen.add(key)
            found.append(token)

    for match in _DURATION.finditer(draft):
        add(match.group(0))
    for match in _PERCENT.finditer(draft):
        add(match.group(0))
    for match in _NUMBER.finditer(draft):
        # Skip numbers already covered by a duration or percent span.
        start, end = match.span()
        covered = any(
            m.start() <= start < m.end()
            for m in list(_DURATION.finditer(draft)) + list(_PERCENT.finditer(draft))
        )
        if not covered:
            add(match.group(0))
    for match in _PROPER.finditer(draft):
        phrase = match.group(1)
        if phrase.split()[0] in _STOP_PROPER:
            continue
        add(phrase)
    for match in _WORD.finditer(draft):
        word = match.group(0)
        if word.lower() in _TECH:
            add(word)
    return tuple(found)


def _token_in_corpus(token: str, corpus: str) -> bool:
    needle = normalise_text(token).lower()
    if not needle:
        return True
    if needle in corpus:
        return True
    # Percentages may appear without the sign in spans ("40 percent").
    if needle.endswith("%") and needle[:-1] in corpus:
        return True
    # Multi-word employers: require every significant word.
    parts = [p for p in re.split(r"\s+", needle) if len(p) > 2]
    if len(parts) > 1 and all(p in corpus for p in parts):
        return True
    return False
