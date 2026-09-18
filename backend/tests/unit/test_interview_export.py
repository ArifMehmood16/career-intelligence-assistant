"""Phase 10.5/10.7 — interview pack sections and markdown export."""

from __future__ import annotations

from pathlib import Path

from career_assistant.application.scoring.rubric_loader import load_scoring_rubric
from career_assistant.domain.claims import Claim
from career_assistant.domain.generation import (
    build_gap_plan,
    build_interview_pack,
    export_markdown,
)
from career_assistant.domain.mapping import map_requirements
from career_assistant.domain.requirements import Requirement

ROOT = Path(__file__).resolve().parents[3]
RUBRIC = load_scoring_rubric(ROOT / "config" / "scoring_rubric.toml")


def _req(id: str, text: str, *, vague: bool = False) -> Requirement:
    return Requirement(
        id=id,
        text=text,
        competency=id,
        seniority_signal=None,
        must_have=True,
        source_span_id=f"jd-{id}",
        extraction_confidence=0.5 if vague else 0.9,
        is_vague=vague,
    )


def _claim(id: str, competency: str, context: str) -> Claim:
    return Claim(
        id=id,
        competency=competency,
        context=context,
        duration_signal="2y",
        recency_signal="recent",
        source_span_ids=(f"cv-{id}",),
        extraction_confidence=0.9,
    )


def test_interview_pack_sections_from_mapping() -> None:
    requirements = (
        _req("dbt", "Production dbt"),
        _req("cuda", "CUDA experience"),
        _req("culture", "Ownership mindset", vague=True),
    )
    claims = (_claim("c1", "dbt", "Owned dbt models in production."),)
    mappings = map_requirements(requirements, claims)
    pack = build_interview_pack(requirements, mappings, claims)
    probe_ids = {p.requirement_id for p in pack.probes}
    assert "dbt" in probe_ids and "cuda" in probe_ids
    assert any(item.requirement_id == "dbt" for item in pack.lead_with)
    assert any(item.requirement_id == "cuda" for item in pack.thin_areas)
    assert any(q.requirement_id == "culture" for q in pack.ask_them)


def test_markdown_export_matches_gap_plan_content() -> None:
    requirements = (
        _req("cuda", "CUDA experience"),
        _req("dbt", "Production dbt"),
    )
    claims = (_claim("c1", "dbt", "Owned dbt models in production."),)
    mappings = map_requirements(requirements, claims)
    plan = build_gap_plan(requirements, mappings, claims, RUBRIC)
    md = export_markdown("gap-plan", plan)
    assert "CUDA" in md or "cuda" in md.lower()
    assert str(int(plan.current_score)) in md or f"{plan.current_score:.0f}" in md
    # Re-export is byte-identical.
    assert md == export_markdown("gap-plan", plan)
