"""PDF text is visual lines, not sentences.

pypdf returns one string per printed line, so a two-line bullet reached span
building as two fragments ("The same answers" / "always give the same result").
A 2026-09-24 CV produced 152 candidate spans from the PDF against 106 from the
same CV as DOCX; the extra fragments failed the evidence-support gate and gave
the model more ids to skip, and the job failed with extraction_incomplete.

Reflow joins a line to the next only when the line runs to the text width and
the next line is plainly a continuation. Everything else stays a line break.
"""

from __future__ import annotations

from career_assistant.parsing.reflow import reflow_wrapped_lines

_WIDE = "x" * 20  # a full-width sentence, so the width reference is realistic

PAGE = "\n".join(
    [
        "EXPERIENCE",
        "Platform Engineer — Northwind Energy Ltd Jan 2024 – Present",
        "Manchester, UK",
        "Product: A trading platform that settles half-hourly electricity "
        "positions for suppliers. Live in",
        "production for two years.",
        "Technologies: Python · FastAPI · PostgreSQL · AWS Lambda behind API Gateway ·",
        "DynamoDB · GitHub Actions",
        "- Built the settlement service that prices every position. The same answers",
        "always give the same result, and tests hold it to the reference "
        "model exactly.",
        "- Split the pricing monolith into four services behind a single "
        "gateway, so each",
        "market integration could release on its own schedule without a shared freeze.",
        "- Led incident response.",
        "Skills: Python, SQL, TypeScript, event-driven processing, PostgreSQL design",
        "Languages: English, Welsh",
        "Settlement Tools github.com/example/settlement-tools",
        "Upload a position file and it explains every price it produced "
        "in plain words.",
        "",
        "EDUCATION",
        "BEng Electrical Engineering — Synthetic University Sep 2014 – Jun 2018",
    ]
)


def test_a_wrapped_sentence_is_rejoined_into_one_line() -> None:
    lines = reflow_wrapped_lines(PAGE).split("\n")

    assert (
        "- Built the settlement service that prices every position. The same answers "
        "always give the same result, and tests hold it to the reference model exactly."
    ) in lines
    assert any(line.endswith("Live in production for two years.") for line in lines)
    assert (
        "Technologies: Python · FastAPI · PostgreSQL · AWS Lambda behind API Gateway · "
        "DynamoDB · GitHub Actions"
    ) in lines


def test_bullets_labels_headings_and_dated_lines_are_never_joined() -> None:
    lines = reflow_wrapped_lines(PAGE).split("\n")

    assert "EXPERIENCE" in lines
    assert "Platform Engineer — Northwind Energy Ltd Jan 2024 – Present" in lines
    assert "Manchester, UK" in lines
    assert "- Led incident response." in lines
    assert "Languages: English, Welsh" in lines
    assert "Settlement Tools github.com/example/settlement-tools" in lines
    education = "BEng Electrical Engineering — Synthetic University Sep 2014 – Jun 2018"
    assert education in lines


def test_paragraph_breaks_survive() -> None:
    assert "\n\nEDUCATION\n" in reflow_wrapped_lines(PAGE)


def test_a_short_line_without_punctuation_is_not_a_wrap() -> None:
    text = "\n".join(
        [_WIDE * 6 + ".", "Owned the release plan", "Ran the incident rota."]
    )

    assert reflow_wrapped_lines(text).split("\n")[1:] == [
        "Owned the release plan",
        "Ran the incident rota.",
    ]


def test_reflow_is_idempotent_and_keeps_empty_text_empty() -> None:
    once = reflow_wrapped_lines(PAGE)

    assert reflow_wrapped_lines(once) == once
    assert reflow_wrapped_lines("") == ""


def test_pdf_intake_gives_whole_sentence_spans_with_valid_offsets() -> None:
    from datetime import UTC, datetime

    from tests.support.document_bytes import make_pdf_bytes

    from career_assistant.domain.documents import DocumentKind
    from career_assistant.parsing.pipeline import parse_document

    parsed = parse_document(
        make_pdf_bytes([PAGE]),
        filename="cv.pdf",
        kind=DocumentKind.CV,
        document_id="cv-pdf-wrapped",
        parsed_at=datetime(2026, 9, 24, tzinfo=UTC),
    )

    page = parsed.pages[0]
    assert (
        "The same answers always give the same result, and tests hold it to the "
        "reference model exactly."
    ) in page.text
    for span in parsed.spans:
        assert page.text[span.start_offset : span.end_offset] == span.text


_JD_ITEMS = [
    "Building and owning backend services in Python and the APIs around them",
    "Developing scalable APIs and data-heavy systems for real-time operational use",
    "Designing products that process large volumes of real-time information daily",
    "Working closely with Product to deliver features end-to-end",
]
_JD_PAGE = "\n".join(
    [
        "We are building an entirely new platform from the ground up combining "
        "real-time data and",
        "distributed hardware, AI, and energy trading to solve complex problems "
        "that matter today.",
        "What You'll Be Doing",
        *_JD_ITEMS,
    ]
)


def test_list_items_without_bullet_glyphs_stay_separate() -> None:
    # A job advert rendered to PDF often loses its bullet glyphs. Joining those
    # lines would merge distinct requirements into one span (PLAN 13D.6c).
    lines = reflow_wrapped_lines(_JD_PAGE).split("\n")

    assert lines[-len(_JD_ITEMS) :] == _JD_ITEMS


def test_a_wrap_after_a_connecting_word_joins_a_capitalised_continuation() -> None:
    first = "- Moved the nightly settlement batch and its retry queue off cron onto"
    second = "AWS Step Functions, so failures resume where they stopped."
    text = "\n".join([_WIDE * 4 + ".", first, second, _WIDE * 4 + "."])

    assert f"{first} {second}" in reflow_wrapped_lines(text).split("\n")
