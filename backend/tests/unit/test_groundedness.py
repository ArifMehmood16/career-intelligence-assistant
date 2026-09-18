"""Phase 10.1 — groundedness validator (pure domain, adversarial fixtures)."""

from __future__ import annotations

from career_assistant.domain.groundedness import (
    GroundednessVerdict,
    validate_groundedness,
)


def test_draft_passes_when_all_tokens_appear_in_spans() -> None:
    draft = "Led dbt migrations on Snowflake for 2 years at Acme Corp."
    spans = (
        "Owned dbt models in production on Snowflake at Acme Corp.",
        "Worked there for 2 years on analytics engineering.",
    )
    result = validate_groundedness(draft, spans)
    assert result.verdict is GroundednessVerdict.PASS
    assert result.ungrounded_tokens == ()


def test_changed_figure_fails_closed() -> None:
    draft = "Reduced pipeline cost by 40% using dbt."
    spans = ("Reduced pipeline cost by 25% using dbt on Snowflake.",)
    result = validate_groundedness(draft, spans)
    assert result.verdict is GroundednessVerdict.FAIL
    assert any("40" in t or "40%" in t for t in result.ungrounded_tokens)


def test_added_technology_fails_closed() -> None:
    draft = "Built Airflow DAGs and Kubernetes operators for Spark jobs."
    spans = ("Built Airflow DAGs for batch Spark jobs on the data platform.",)
    result = validate_groundedness(draft, spans)
    assert result.verdict is GroundednessVerdict.FAIL
    assert any("kubernetes" in t.lower() for t in result.ungrounded_tokens)


def test_inflated_duration_fails_closed() -> None:
    draft = "Owned the dbt project for 5 years."
    spans = ("Owned the dbt project for 2 years at Acme.",)
    result = validate_groundedness(draft, spans)
    assert result.verdict is GroundednessVerdict.FAIL
    assert any("5" in t or "5 years" in t.lower() for t in result.ungrounded_tokens)


def test_renamed_employer_fails_closed() -> None:
    draft = "Shipped analytics at Globex Industries."
    spans = ("Shipped analytics dashboards at Acme Corp.",)
    result = validate_groundedness(draft, spans)
    assert result.verdict is GroundednessVerdict.FAIL
    assert any("globex" in t.lower() for t in result.ungrounded_tokens)


def test_empty_draft_passes_with_no_tokens() -> None:
    result = validate_groundedness("   ", ("Owned dbt models.",))
    assert result.verdict is GroundednessVerdict.PASS
    assert result.ungrounded_tokens == ()


def test_normalisation_allows_case_and_punctuation_variants() -> None:
    draft = "Used DBT and snowflake."
    spans = ("Used dbt and Snowflake in production.",)
    result = validate_groundedness(draft, spans)
    assert result.verdict is GroundednessVerdict.PASS
