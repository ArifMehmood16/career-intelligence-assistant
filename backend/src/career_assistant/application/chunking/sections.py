"""Split a document into sections that each fit one structure call (PLAN 18.4).

A document that fits the provider's input window is one call. Otherwise it is cut
at server-detected headings — a short line that ends in a colon, is written in
capitals or starts with '#' — packing whole blocks into each section, and a single
block that is still too big is cut into windows. Line numbers stay global. The
structure reply is small, so the output cap does not decide the cut.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from career_assistant.domain.lines import NumberedLine

# Starting estimate, not a measurement. The structure reply is ranges and kinds,
# so only the input window sizes a section.
PROMPT_OVERHEAD_TOKENS = 1_200
_HEADING_MAX_CHARS = 60
_BULLETS = ("-", "*", "•", "–")

Section = tuple[NumberedLine, ...]


@dataclass(frozen=True, slots=True)
class ChunkingBudget:
    max_input_tokens: int

    def fits(self, lines: Sequence[NumberedLine]) -> bool:
        return section_input_tokens(lines) <= self.max_input_tokens


def section_input_tokens(lines: Sequence[NumberedLine]) -> int:
    return PROMPT_OVERHEAD_TOKENS + sum(len(line.text) // 4 + 4 for line in lines)


def plan_sections(
    lines: Sequence[NumberedLine], budget: ChunkingBudget
) -> tuple[Section, ...]:
    if budget.fits(lines):
        return (tuple(lines),)
    sections: list[Section] = []
    current: list[NumberedLine] = []
    for block in _blocks(lines):
        if current and budget.fits([*current, *block]):
            current.extend(block)
            continue
        if current:
            sections.append(tuple(current))
        current = list(block) if budget.fits(block) else []
        if not current:
            sections.extend(_windows(block, budget))
    if current:
        sections.append(tuple(current))
    return tuple(sections)


def is_heading(line: NumberedLine) -> bool:
    text = line.text
    if len(text) > _HEADING_MAX_CHARS or text.startswith(_BULLETS):
        return False
    shouting = text.isupper() and any(c.isalpha() for c in text)
    return text.endswith(":") or text.startswith("#") or shouting


def _blocks(lines: Sequence[NumberedLine]) -> list[Section]:
    blocks: list[list[NumberedLine]] = []
    for line in lines:
        if not blocks or is_heading(line):
            blocks.append([line])
        else:
            blocks[-1].append(line)
    return [tuple(block) for block in blocks]


def _windows(block: Section, budget: ChunkingBudget) -> list[Section]:
    windows: list[Section] = []
    current: list[NumberedLine] = []
    for line in block:
        if current and not budget.fits([*current, line]):
            windows.append(tuple(current))
            current = []
        current.append(line)
    if current:
        windows.append(tuple(current))
    return windows
