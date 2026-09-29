"""Server-numbered lines: the unit the model groups into chunks (ADR 013).

Numbering is a pure function of the stored normalised text, so the same document
always yields the same lines and a chunk's line range can be resolved back to
exact offsets without storing the lines.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NumberedLine:
    number: int
    start_offset: int
    end_offset: int
    text: str


def number_lines(text: str) -> tuple[NumberedLine, ...]:
    lines: list[NumberedLine] = []
    offset = 0
    for raw in text.split("\n"):
        stripped = raw.strip()
        if stripped:
            start = offset + (len(raw) - len(raw.lstrip()))
            lines.append(
                NumberedLine(
                    number=len(lines) + 1,
                    start_offset=start,
                    end_offset=start + len(stripped),
                    text=stripped,
                )
            )
        offset += len(raw) + 1
    return tuple(lines)
