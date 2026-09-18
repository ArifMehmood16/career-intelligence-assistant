"""Plain-text page extraction."""

from __future__ import annotations

from career_assistant.domain.normalisation import normalise_text


def extract_plain_text_pages(data: bytes) -> list[str]:
    text = data.decode("utf-8")
    normalised = normalise_text(text)
    return [normalised] if normalised else [""]
