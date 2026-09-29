"""The server numbers the lines; the model groups them (ADR 013)."""

from __future__ import annotations

from career_assistant.domain.lines import number_lines

_TEXT = "Jane Doe\njane@example.com\n\nExperience\n- Built hybrid retrieval\n  over pgvector.\n"


def test_non_empty_lines_are_numbered_from_one() -> None:
    lines = number_lines(_TEXT)

    assert [line.number for line in lines] == [1, 2, 3, 4, 5]
    assert lines[2].text == "Experience"


def test_offsets_point_back_into_the_stored_text() -> None:
    lines = number_lines(_TEXT)

    for line in lines:
        assert _TEXT[line.start_offset : line.end_offset] == line.text


def test_surrounding_whitespace_is_outside_the_line() -> None:
    lines = number_lines(_TEXT)

    assert lines[4].text == "over pgvector."
    assert _TEXT[lines[4].start_offset - 2 : lines[4].start_offset] == "  "


def test_numbering_is_deterministic() -> None:
    assert number_lines(_TEXT) == number_lines(_TEXT)


def test_blank_text_has_no_lines() -> None:
    assert number_lines("\n \n\t\n") == ()
