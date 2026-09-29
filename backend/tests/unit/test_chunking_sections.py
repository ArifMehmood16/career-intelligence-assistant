"""A document too big for one call is split at its headings (PLAN 18.4)."""

from __future__ import annotations

from career_assistant.application.chunking.sections import ChunkingBudget, plan_sections
from career_assistant.domain.lines import number_lines

_DOC = "\n".join(
    [
        "Jane Doe",
        "EXPERIENCE",
        *[f"- Delivered piece of work number {i}." for i in range(1, 9)],
        "Education:",
        "MSc Computer Science, 2016",
        "SKILLS",
        "Python, SQL",
    ]
)


def _budget(output_lines: int) -> ChunkingBudget:
    return ChunkingBudget(max_input_tokens=100_000, max_output_tokens=output_lines * 40)


def test_a_document_that_fits_is_one_section() -> None:
    lines = number_lines(_DOC)

    sections = plan_sections(lines, _budget(output_lines=100))

    assert sections == (lines,)


def test_sections_start_at_headings_and_cover_every_line_once() -> None:
    lines = number_lines(_DOC)

    sections = plan_sections(lines, _budget(output_lines=11))

    assert [s[0].text for s in sections] == ["Jane Doe", "Education:"]
    assert [n.number for s in sections for n in s] == [n.number for n in lines]


def test_a_block_longer_than_the_budget_is_cut_into_windows() -> None:
    lines = number_lines(_DOC)

    sections = plan_sections(lines, _budget(output_lines=3))

    assert all(len(s) <= 3 for s in sections)
    assert [n.number for s in sections for n in s] == [n.number for n in lines]


def test_the_input_budget_also_splits() -> None:
    lines = number_lines(_DOC)
    tight = ChunkingBudget(max_input_tokens=60, max_output_tokens=100_000)

    sections = plan_sections(lines, tight)

    assert len(sections) > 1
