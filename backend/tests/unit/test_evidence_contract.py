"""PLAN 13D.2 — the evidence contract is one accepted ADR, reconciled in the docs.

The running matcher is unchanged here. This test fails while the documents still
say an uploaded letter can never affect a score, or that a citation is support.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ADR = ROOT / "docs" / "adr" / "011-evidence-assessment-contract.md"
AGENTS = ROOT / "AGENTS.md"
FEATURES = ROOT / "docs" / "features.md"
ADR_004 = ROOT / "docs" / "adr" / "004-deterministic-scoring.md"
ADR_009 = ROOT / "docs" / "adr" / "009-vectors-propose-mapping-candidates.md"
ADR_010 = ROOT / "docs" / "adr" / "010-model-first-extraction.md"


def test_adr_011_separates_assessment_validation_and_scoring() -> None:
    assert ADR.is_file(), "ADR 011 is required by PLAN 13D.2"
    text = ADR.read_text(encoding="utf-8").lower()
    assert "- status: accepted" in text
    for needle in (
        "model assesses",
        "server validates",
        "domain calculates",
        "citation",
        "does not prove",
        "concrete experience",
        "uploaded letter",
        "duplicates",
        "aspiration",
        "generated draft",
        "never raise the score",
    ):
        assert needle in text, f"ADR 011 missing {needle!r}"


def test_agents_and_features_follow_the_letter_policy() -> None:
    agents = AGENTS.read_text(encoding="utf-8")
    features = FEATURES.read_text(encoding="utf-8")
    assert "must never produce claims or affect" not in agents
    assert "never count as proof of experience" not in features
    assert "Neither uploaded nor generated letter text can affect a fit score" not in features
    for document in (agents, features):
        lowered = document.lower()
        assert "adr 011" in lowered
        assert "generated draft" in lowered
        assert "aspiration" in lowered
        assert "duplicate" in lowered


def test_earlier_adrs_point_at_the_evidence_contract() -> None:
    for path in (ADR_004, ADR_009, ADR_010):
        text = path.read_text(encoding="utf-8").lower()
        assert "adr 011" in text, f"{path.name} does not reconcile with ADR 011"
    scoring = ADR_004.read_text(encoding="utf-8").lower()
    assert "citation" in scoring
    assert "does not prove" in scoring
