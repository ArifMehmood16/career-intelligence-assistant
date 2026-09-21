"""PLAN 13C.9 — the deterministic fixture path must survive real PDF text.

The 2026-09-21 output audit ran a real CV through the shipped pipeline and got
zero claims. `pypdf` emits list items as `•Text` with no following space,
normalisation rewrites that to `-Text`, and the bullet pattern required
whitespace after the glyph. Two further shapes broke the same document: a
wrapped body line beginning with a section word ended the experience section
mid-CV, and abbreviated month ranges on the role line never parsed, so every
claim came out undated.

These are regressions, not new features. The rules extractors stay the hermetic
test fixture, so they have to be honest about the text a parser really produces.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from career_assistant.adapters.extraction.claims_rules import RulesClaimExtractor
from career_assistant.adapters.extraction.rules import RulesRequirementExtractor
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.normalisation import normalise_text

ROOT = Path(__file__).resolve().parents[3]
CV_PDF_SHAPED = ROOT / "sample-data" / "fixtures" / "resumes" / "cv-pdf-extracted.txt"
AS_OF = date(2026, 9, 21)


def _claims(text: str):
    return RulesClaimExtractor(as_of=AS_OF).extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=normalise_text(text),
    )


def _requirements(text: str):
    return RulesRequirementExtractor().extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=normalise_text(text),
    )


def test_claim_bullet_without_space_after_the_glyph_is_extracted() -> None:
    result = _claims(CV_PDF_SHAPED.read_text(encoding="utf-8"))

    assert result.claims, "a bullet with no space after the glyph must still parse"
    assert any("Owned the AI layer" in claim.context for claim in result.claims)


def test_wrapped_line_beginning_with_a_section_word_does_not_end_experience() -> None:
    # "education customers. Live in production..." is a body line, not a heading.
    result = _claims(CV_PDF_SHAPED.read_text(encoding="utf-8"))

    contexts = " ".join(claim.context for claim in result.claims)
    assert "serverless backend" in contexts, "the second role must still be extracted"
    assert "Ran the client relationship" in contexts


def test_a_real_heading_still_ends_the_experience_section() -> None:
    result = _claims(CV_PDF_SHAPED.read_text(encoding="utf-8"))

    assert not any("BSc Computer Science" in c.context for c in result.claims)


def test_abbreviated_month_range_on_the_role_line_gives_a_recency_signal() -> None:
    result = _claims(CV_PDF_SHAPED.read_text(encoding="utf-8"))

    current = [c for c in result.claims if "Owned the AI layer" in c.context]
    assert current, "expected the current role's claims"
    assert current[0].recency_signal == "recent"
    assert current[0].duration_signal != "undated"


def test_requirement_bullet_without_space_after_the_glyph_is_extracted() -> None:
    advert = (
        "What you'll do\n"
        "•Build and operate agents in production for named client accounts\n"
        "•Read run traces, debug and fix at the agent level\n"
    )

    result = _requirements(advert)

    assert len(result.requirements) == 2
    assert result.requirements[0].text.startswith("Build and operate agents")


def test_every_extracted_span_round_trips_to_its_source_text() -> None:
    text = normalise_text(CV_PDF_SHAPED.read_text(encoding="utf-8"))
    result = _claims(CV_PDF_SHAPED.read_text(encoding="utf-8"))

    for span in result.spans:
        assert text[span.start_offset : span.end_offset] == span.text


def test_a_wrapped_bullet_is_truncated_at_the_line_break() -> None:
    """Recorded limitation, not desired behaviour.

    The rules extractor reads one line per bullet, so a bullet that wraps loses
    everything after the first line. It is kept as the hermetic fixture and this
    is what a fixture is allowed to be; PLAN 13C.3 removes the problem by having
    the model return a verbatim quote that the server verifies. This test exists
    so the limitation is visible rather than discovered again in a demo.
    """
    result = _claims(CV_PDF_SHAPED.read_text(encoding="utf-8"))

    wrapped = [c for c in result.claims if "Ran the client relationship" in c.context]
    assert wrapped
    assert "trained the colleagues" not in wrapped[0].context
