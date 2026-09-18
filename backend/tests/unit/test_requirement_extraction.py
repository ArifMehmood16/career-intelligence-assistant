"""Phase 5 — requirement domain and extraction behaviours."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_assistant.adapters.extraction.rules import RulesRequirementExtractor
from career_assistant.application.extraction.validate import (
    validate_requirements_against_pages,
)
from career_assistant.domain.documents import DocumentKind, Page, Span
from career_assistant.domain.normalisation import normalise_text
from career_assistant.domain.requirements import Requirement

ROOT = Path(__file__).resolve().parents[3]
JD_DIR = ROOT / "sample-data" / "fixtures" / "job-descriptions"


def _load_jd(name: str) -> str:
    return normalise_text((JD_DIR / name).read_text(encoding="utf-8"))


def test_requirement_domain_fields_are_explicit() -> None:
    req = Requirement(
        id="req-1",
        text="Production experience with dbt",
        competency="dbt",
        seniority_signal=None,
        must_have=True,
        source_span_id="span-1",
        extraction_confidence=0.9,
        is_vague=False,
    )
    assert req.must_have is True
    assert req.competency == "dbt"
    assert req.source_span_id == "span-1"


def test_rules_extractor_reads_bulleted_must_and_desirable_sections() -> None:
    text = _load_jd("jd-clean-match.txt")
    extractor = RulesRequirementExtractor()
    result = extractor.extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=text,
    )
    assert len(result.requirements) >= 4
    joined = " ".join(r.text.lower() for r in result.requirements)
    assert "dbt" in joined
    assert "sql" in joined
    assert "python" in joined
    desirables = [r for r in result.requirements if not r.must_have]
    assert desirables, "Looker / nice-to-have bullets should be desirable"
    assert all(r.source_span_id for r in result.requirements)


def test_six_fixture_jds_produce_requirements_with_resolvable_spans() -> None:
    extractor = RulesRequirementExtractor()
    for path in sorted(JD_DIR.glob("jd-*.txt")):
        text = _load_jd(path.name)
        page = Page(document_id="doc-jd", page_number=1, text=text)
        result = extractor.extract(
            document_id="doc-jd",
            document_kind=DocumentKind.JOB_DESCRIPTION,
            normalised_text=text,
        )
        assert result.requirements, f"{path.name} produced no requirements"
        kept, dropped = validate_requirements_against_pages(
            result.requirements, result.spans, pages=(page,)
        )
        assert dropped == 0, f"{path.name} dropped {dropped} requirements"
        assert kept
        assert all(isinstance(r, Requirement) for r in kept)


def test_invalid_source_span_is_dropped_not_passed_through() -> None:
    page = Page(document_id="doc-jd", page_number=1, text="Real requirement text here.")
    good_span = Span(
        id="span-good",
        document_id="doc-jd",
        page_number=1,
        start_offset=0,
        end_offset=4,
        text="Real",
    )
    bad_span = Span(
        id="span-bad",
        document_id="doc-jd",
        page_number=1,
        start_offset=0,
        end_offset=4,
        text="FAKE",
    )
    requirements = (
        Requirement(
            id="r1",
            text="Real",
            competency="general",
            seniority_signal=None,
            must_have=True,
            source_span_id="span-good",
            extraction_confidence=1.0,
            is_vague=False,
        ),
        Requirement(
            id="r2",
            text="Invented",
            competency="general",
            seniority_signal=None,
            must_have=True,
            source_span_id="span-bad",
            extraction_confidence=1.0,
            is_vague=False,
        ),
    )
    kept, dropped = validate_requirements_against_pages(
        requirements, (good_span, bad_span), pages=(page,)
    )
    assert dropped == 1
    assert len(kept) == 1
    assert kept[0].id == "r1"


def test_injection_fixture_does_not_add_override_requirements() -> None:
    extractor = RulesRequirementExtractor()
    text = _load_jd("jd-injection-attempt.txt")
    result = extractor.extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=text,
    )
    joined = " ".join(r.text.lower() for r in result.requirements)
    assert "perfect match" not in joined
    assert "fit score" not in joined
    assert "cuda" not in joined
    assert "ros2" not in joined
    assert any("dbt" in r.text.lower() for r in result.requirements)


def test_vague_seniority_fixture_marks_unquantified_signals() -> None:
    extractor = RulesRequirementExtractor()
    text = _load_jd("jd-vague-seniority.txt")
    result = extractor.extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=text,
    )
    assert result.requirements
    assert any(r.is_vague for r in result.requirements)
    assert any(r.seniority_signal for r in result.requirements)


def test_cover_letter_cannot_contribute_requirements() -> None:
    extractor = RulesRequirementExtractor()
    with pytest.raises(ValueError, match="cover_letter"):
        extractor.extract(
            document_id="doc-cl",
            document_kind=DocumentKind.COVER_LETTER,
            normalised_text="- Pretend this is a must-have requirement.",
        )


def test_model_backed_extractor_accepts_only_span_backed_texts() -> None:
    from career_assistant.adapters.extraction.model_backed import (
        ModelRequirementExtractor,
    )
    from career_assistant.adapters.providers.hermetic.completion import (
        HermeticCompletionAdapter,
    )

    text = _load_jd("jd-clean-match.txt")
    page = Page(document_id="doc-jd", page_number=1, text=text)
    extractor = ModelRequirementExtractor(HermeticCompletionAdapter())
    result = extractor.extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=text,
    )
    kept, dropped = validate_requirements_against_pages(
        result.requirements, result.spans, pages=(page,)
    )
    assert dropped == 0
    assert kept
    assert any("dbt" in r.text.lower() for r in kept)
