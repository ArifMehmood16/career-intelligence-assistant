"""A document too big for one call is split at its headings (PLAN 18.4)."""

from __future__ import annotations

from career_assistant.application.chunking.sections import (
    ChunkingBudget,
    plan_sections,
    section_input_tokens,
)
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


def test_a_document_that_fits_is_one_section() -> None:
    lines = number_lines(_DOC)

    sections = plan_sections(
        lines, ChunkingBudget(max_input_tokens=section_input_tokens(lines))
    )

    assert sections == (lines,)


def test_sections_start_at_headings_and_cover_every_line_once() -> None:
    lines = number_lines(_DOC)
    education = next(
        index for index, line in enumerate(lines) if line.text == "Education:"
    )

    sections = plan_sections(
        lines, ChunkingBudget(max_input_tokens=section_input_tokens(lines[:education]))
    )

    assert sections[0][0].text == "Jane Doe"
    assert any(section[0].text == "Education:" for section in sections)
    assert [line.number for section in sections for line in section] == [
        line.number for line in lines
    ]


def test_a_block_longer_than_the_budget_is_cut_into_windows() -> None:
    lines = number_lines(_DOC)

    sections = plan_sections(
        lines, ChunkingBudget(max_input_tokens=section_input_tokens(lines[:1]))
    )

    assert len(sections) > 1
    assert [line.number for section in sections for line in section] == [
        line.number for line in lines
    ]


def test_the_input_budget_splits_a_document_that_does_not_fit() -> None:
    lines = number_lines(_DOC)
    tight = ChunkingBudget(max_input_tokens=section_input_tokens(lines) - 1)

    sections = plan_sections(lines, tight)

    assert len(sections) > 1
    assert [line.number for section in sections for line in section] == [
        line.number for line in lines
    ]
