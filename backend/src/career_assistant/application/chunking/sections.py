"""Split a document into sections that each fit one chunking call (PLAN 18.4).

A document that fits the provider's budget is one call. Otherwise it is cut at
server-detected headings — a short line that ends in a colon, is written in
capitals or starts with '#' — packing whole blocks into each section, and a single
block that is still too big is cut into windows. Line numbers stay global.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from career_assistant.domain.lines import NumberedLine

# Starting estimates, not measurements; 18.14 revisits them with observed usage.
PROMPT_OVERHEAD_TOKENS = 1_200
OUTPUT_TOKENS_PER_LINE = 40
_HEADING_MAX_CHARS = 60
_BULLETS = ("-", "*", "•", "–")

Section = tuple[NumberedLine, ...]


@dataclass(frozen=True, slots=True)
class ChunkingBudget:
    max_input_tokens: int
    max_output_tokens: int

    def fits(self, lines: Sequence[NumberedLine]) -> bool:
        input_tokens = PROMPT_OVERHEAD_TOKENS + sum(_input_tokens(n) for n in lines)
        output_tokens = OUTPUT_TOKENS_PER_LINE * len(lines)
        return (
            input_tokens <= self.max_input_tokens
            and output_tokens <= self.max_output_tokens
        )


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


def _input_tokens(line: NumberedLine) -> int:
    # Roughly four characters a token, plus the "L123: " prefix.
    return len(line.text) // 4 + 4
