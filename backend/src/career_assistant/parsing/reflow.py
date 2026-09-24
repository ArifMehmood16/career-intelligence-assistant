"""Rejoin PDF lines that wrapped mid-sentence.

pypdf returns the printed lines of a page, so one sentence that wraps becomes
two candidate spans. Joining is conservative: a line is treated as wrapped only
when it runs close to the page's text width and ends without punctuation, and
the next line reads as a continuation. Bullets, ``Label:`` lines, headings,
dated role or education lines and contact lines always keep their break.
DOCX paragraphs are already whole and never pass through here.
"""

from __future__ import annotations

import math
import re

from career_assistant.domain.recency import parse_date_range

# A wrapped line fills most of the column; the 90th percentile tolerates a few
# over-long lines such as a tab-aligned heading.
_WIDTH_PERCENTILE = 0.9
_WRAP_FRACTION = 0.75
_MIN_LINES_FOR_REFERENCE = 3

_TERMINAL = frozenset(".!?:;")
_BULLET = re.compile(r"^[-*]")
_LABEL = re.compile(r"^[A-Z][A-Za-z0-9 &/,+().'-]{0,48}:(?:\s|$)")
_CONTACT = re.compile(
    r"@|https?://|(?:linkedin|github)\.com\b|^\+?\d[\d ()-]{7,}", re.IGNORECASE
)


def reflow_wrapped_lines(text: str) -> str:
    """Join visual lines that belong to one sentence; keep every other break."""
    lines = text.split("\n")
    threshold = _wrap_threshold(lines)
    if threshold is None:
        return text
    out: list[str] = []
    for line in lines:
        if out and _continues(out[-1], line, threshold):
            out[-1] = f"{out[-1]} {line}"
        else:
            out.append(line)
    return "\n".join(out)


def _wrap_threshold(lines: list[str]) -> float | None:
    lengths = sorted(len(line) for line in lines if line.strip())
    if len(lengths) < _MIN_LINES_FOR_REFERENCE:
        return None
    reference = lengths[math.ceil(_WIDTH_PERCENTILE * (len(lengths) - 1))]
    return reference * _WRAP_FRACTION


def _continues(previous: str, line: str, threshold: float) -> bool:
    if not previous.strip() or not line.strip():
        return False
    if len(previous) < threshold or previous[-1] in _TERMINAL:
        return False
    return not (_is_boundary(previous) or _starts_new_unit(line))


def _is_boundary(line: str) -> bool:
    """A line that ends a unit even without punctuation."""
    return _is_heading(line) or _is_dated(line) or _CONTACT.search(line) is not None


def _starts_new_unit(line: str) -> bool:
    return (
        _BULLET.match(line) is not None
        or _LABEL.match(line) is not None
        or _is_boundary(line)
    )


def _is_heading(line: str) -> bool:
    return any(char.isalpha() for char in line) and line == line.upper()


def _is_dated(line: str) -> bool:
    return parse_date_range(line) is not None
