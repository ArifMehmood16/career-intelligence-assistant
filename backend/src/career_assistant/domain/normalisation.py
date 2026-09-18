"""Text normalisation — offsets address the normalised string."""

from __future__ import annotations

import re
import unicodedata

_LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\u00e6": "ae",
    "\u00c6": "AE",
    "\u0153": "oe",
    "\u0152": "OE",
}

_BULLETS = {
    "\u2022": "-",  # •
    "\u2023": "-",  # ‣
    "\u25e6": "-",  # ◦
    "\u2043": "-",  # ⁃
    "\u2219": "-",  # ∙
    "\uf0b7": "-",  # private-use bullet often from Word
}

_SOFT_HYPHEN = "\u00ad"
_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_CRLF = re.compile(r"\r\n?")
_MULTI_SPACE = re.compile(r"[ \t\f\v]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")


def normalise_text(raw: str) -> str:
    """Normalise whitespace, ligatures, bullets and hyphenation at line breaks."""
    text = raw
    for src, dst in _LIGATURES.items():
        text = text.replace(src, dst)
    for src, dst in _BULLETS.items():
        text = text.replace(src, dst)
    text = text.replace(_SOFT_HYPHEN, "")
    text = unicodedata.normalize("NFKC", text)
    text = _CRLF.sub("\n", text)
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def paragraph_spans(page_text: str) -> list[tuple[int, int, str]]:
    """Split normalised page text into paragraph slices (start, end, text)."""
    if not page_text:
        return []
    parts = re.split(r"\n\s*\n", page_text)
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    for part in parts:
        if not part:
            continue
        start = page_text.find(part, cursor)
        if start < 0:
            start = cursor
        end = start + len(part)
        spans.append((start, end, part))
        cursor = end
    if not spans:
        spans.append((0, len(page_text), page_text))
    return spans
