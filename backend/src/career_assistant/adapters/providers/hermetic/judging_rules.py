"""Rule-based judge verdicts for the hermetic fixture (PLAN 18.7).

A test fixture, never a quality claim. A requirement is met when a candidate chunk
names one of its terms, quoted exactly as the chunk writes it; experience is read
from the server's facts. It reads only the prompt layout in
`application/judge/prompt.py`.
"""

from __future__ import annotations

import re
from typing import Any

_REQUIREMENT = re.compile(
    r'<requirement id="([^"\n]+)">\n(.*?)\n</requirement id="\1">', re.DOTALL
)
_CHUNK = re.compile(r'<chunk id="([^"\n]+)">\n(.*?)\n</chunk id="\1">', re.DOTALL)
_FACT = re.compile(r"^- ([^:\n]+): (?:exact|alias only); up to (\d+\.\d) years", re.M)
_TEXT_MARKER = "\ntext:\n"
_NULL = "null"
_RATIONALE = "Rule-based fixture."


def judge_verdicts(user: str) -> dict[str, Any]:
    years = {term: float(value) for term, value in _FACT.findall(user)}
    return {
        "verdicts": [
            _verdict(requirement_id, body, years)
            for requirement_id, body in _REQUIREMENT.findall(user)
        ]
    }


def _verdict(requirement_id: str, body: str, years: dict[str, float]) -> dict[str, Any]:
    fields = _fields(body)
    terms = [t.strip() for t in fields.get("terms", "").split(",") if t.strip()]
    found = _first_named(body, terms)
    evidence = [] if found is None else [{"chunk_id": found[0], "quote": found[1]}]
    score = 3 if found else 0
    verdict: dict[str, Any] = {
        "requirement_id": requirement_id,
        "verdict": "met" if found else "missing",
        "match": {"score": score, "rationale": _RATIONALE, "evidence": evidence},
        "retrieval_feedback": {"sufficient": True},
    }
    if fields.get("seniority_expected", _NULL) != _NULL:
        verdict["seniority"] = {"score": score, "rationale": _RATIONALE}
    expected = fields.get("years_expected", _NULL)
    if expected != _NULL:
        held = max((years.get(t.casefold(), 0.0) for t in terms), default=0.0)
        verdict["experience"] = {
            "score": _experience(held, float(expected), found is not None),
            "rationale": _RATIONALE,
        }
    return verdict


def _fields(body: str) -> dict[str, str]:
    head = body.split("\n<chunk ", 1)[0]
    return dict(line.split(": ", 1) for line in head.split("\n") if ": " in line)


def _first_named(body: str, terms: list[str]) -> tuple[str, str] | None:
    for chunk_id, block in _CHUNK.findall(body):
        text = block.split(_TEXT_MARKER, 1)[-1]
        for term in terms:
            quote = _named(text, term)
            if quote is not None:
                return chunk_id, quote
    return None


def _named(text: str, term: str) -> str | None:
    folded, wanted = text.casefold(), term.casefold()
    start = folded.find(wanted)
    while start >= 0:
        end = start + len(wanted)
        before = folded[start - 1] if start else " "
        after = folded[end] if end < len(folded) else " "
        if not before.isalnum() and not after.isalnum():
            return text[start:end]
        start = folded.find(wanted, start + 1)
    return None


def _experience(held: float, expected: float, found: bool) -> int:
    if held >= expected:
        return 3
    if held >= expected / 2:
        return 2
    return 1 if found else 0
