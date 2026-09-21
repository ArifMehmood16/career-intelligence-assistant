"""Phase 6 — claim / evidence extraction behaviours."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from career_assistant.adapters.extraction.claims_rules import RulesClaimExtractor
from career_assistant.application.extraction.validate import (
    validate_claims_against_pages,
)
from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import DocumentKind, Page, Span
from career_assistant.domain.normalisation import normalise_text
from career_assistant.domain.recency import (
    DateRange,
    derive_duration_signal,
    derive_recency_signal,
    parse_date_range,
)

ROOT = Path(__file__).resolve().parents[3]
CV_DIR = ROOT / "sample-data" / "fixtures" / "resumes"
AS_OF = date(2026, 9, 18)


def _load_cv(name: str) -> str:
    return normalise_text((CV_DIR / name).read_text(encoding="utf-8"))


def test_claim_domain_fields_are_explicit() -> None:
    claim = Claim(
        id="c1",
        competency="dbt",
        context="Owned dbt models in production.",
        duration_signal="2y",
        recency_signal="recent",
        source_span_ids=("span-1",),
        extraction_confidence=0.85,
    )
    assert claim.competency == "dbt"
    assert claim.recency_signal == "recent"
    assert claim.source_span_ids == ("span-1",)


def test_recency_and_duration_come_from_dates_not_assumptions() -> None:
    recent = DateRange(start=date(2023, 1, 1), end=None)
    assert derive_recency_signal(recent, as_of=AS_OF) == "recent"
    assert derive_duration_signal(recent, as_of=AS_OF).endswith("y")

    old = DateRange(start=date(2014, 1, 1), end=date(2020, 1, 1))
    assert derive_recency_signal(old, as_of=AS_OF) == "old"

    assert derive_recency_signal(None, as_of=AS_OF) == "undated"
    assert derive_duration_signal(None, as_of=AS_OF) == "undated"

    assert parse_date_range("January 2023 – Present") == recent
    assert parse_date_range("no dates here") is None


def test_rules_extractor_produces_claims_from_cv_bullets() -> None:
    text = _load_cv("cv-strong-match.txt")
    extractor = RulesClaimExtractor(as_of=AS_OF)
    result = extractor.extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=text,
    )
    assert len(result.claims) >= 4
    joined = " ".join(c.context.lower() for c in result.claims)
    assert "dbt" in joined
    assert "snowflake" in joined or "sql" in joined
    assert all(c.source_span_ids for c in result.claims)
    assert any(c.recency_signal == "recent" for c in result.claims)


def test_three_fixture_cvs_produce_resolvable_claim_spans() -> None:
    extractor = RulesClaimExtractor(as_of=AS_OF)
    for path in sorted(CV_DIR.glob("cv-*.txt")):
        text = _load_cv(path.name)
        page = Page(document_id="doc-cv", page_number=1, text=text)
        result = extractor.extract(
            document_id="doc-cv",
            document_kind=DocumentKind.CV,
            normalised_text=text,
        )
        assert result.claims, f"{path.name} produced no claims"
        kept, dropped = validate_claims_against_pages(
            result.claims, result.spans, pages=(page,)
        )
        assert dropped == 0, f"{path.name} dropped {dropped} claims"
        assert kept


def test_dated_experience_fixture_marks_spark_as_not_recent() -> None:
    text = _load_cv("cv-dated-experience.txt")
    extractor = RulesClaimExtractor(as_of=AS_OF)
    result = extractor.extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=text,
    )
    spark_claims = [
        c
        for c in result.claims
        if "spark" in c.context.lower() or c.competency == "spark"
    ]
    assert spark_claims, "expected Spark evidence from the legacy role"
    assert all(c.recency_signal in {"old", "mid"} for c in spark_claims)
    assert all(c.recency_signal != "recent" for c in spark_claims)

    recentish = [
        c
        for c in result.claims
        if "airflow" in c.context.lower() or "bigquery" in c.context.lower()
    ]
    assert recentish
    assert any(c.recency_signal == "recent" for c in recentish)


def test_invalid_claim_span_is_dropped() -> None:
    page = Page(document_id="doc-cv", page_number=1, text="Owned dbt models.")
    good = Span(
        id="s-good",
        document_id="doc-cv",
        page_number=1,
        start_offset=0,
        end_offset=5,
        text="Owned",
    )
    bad = Span(
        id="s-bad",
        document_id="doc-cv",
        page_number=1,
        start_offset=0,
        end_offset=5,
        text="FAKE!",
    )
    claims = (
        Claim(
            id="c1",
            competency="dbt",
            context="Owned",
            duration_signal="1y",
            recency_signal="recent",
            source_span_ids=("s-good",),
            extraction_confidence=0.9,
        ),
        Claim(
            id="c2",
            competency="dbt",
            context="Invented",
            duration_signal="undated",
            recency_signal="undated",
            source_span_ids=("s-bad",),
            extraction_confidence=0.9,
        ),
    )
    kept, dropped = validate_claims_against_pages(claims, (good, bad), pages=(page,))
    assert dropped == 1
    assert len(kept) == 1
    assert kept[0].id == "c1"


def test_cover_letter_claims_are_self_authored_not_score_evidence() -> None:
    extractor = RulesClaimExtractor(as_of=AS_OF)
    result = extractor.extract(
        document_id="doc-cl",
        document_kind=DocumentKind.COVER_LETTER,
        normalised_text="- I have production dbt experience.",
    )
    assert result.claims
    assert all(c.self_authored for c in result.claims)


def test_model_backed_claim_extractor_keeps_span_backed_texts() -> None:
    from career_assistant.adapters.extraction.claims_model import ModelClaimExtractor
    from career_assistant.adapters.providers.hermetic.completion import (
        HermeticCompletionAdapter,
    )

    text = _load_cv("cv-strong-match.txt")
    page = Page(document_id="doc-cv", page_number=1, text=text)
    extractor = ModelClaimExtractor(HermeticCompletionAdapter(), as_of=AS_OF)
    result = extractor.extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=text,
    )
    kept, dropped = validate_claims_against_pages(
        result.claims, result.spans, pages=(page,)
    )
    assert dropped == 0
    assert kept
    assert any("dbt" in c.context.lower() for c in kept)
