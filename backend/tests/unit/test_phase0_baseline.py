"""Phase 0 exit gate: decisions recorded, fixtures exist, no product inventiveness.

These tests pin the repository baseline that later phases rely on. They fail when a
documented decision, fixture scenario or evaluation shape is missing — not when a
model is clever.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AGENTS = ROOT / "AGENTS.md"
FEATURES = ROOT / "docs" / "features.md"
THREAT_MODEL = ROOT / "docs" / "threat-model.md"
EVALUATION = ROOT / "docs" / "evaluation.md"
ADR_DIR = ROOT / "docs" / "adr"
FIXTURES = ROOT / "sample-data" / "fixtures"
MANIFEST = FIXTURES / "manifest.json"
DATASET = ROOT / "sample-data" / "evaluation" / "dataset.json"
RUBRIC = ROOT / "config" / "scoring_rubric.toml"

INVARIANT = "The model extracts. The domain decides."

REQUIRED_ADRS = {
    "001-modular-monolith.md": ("modular monolith", "domain", "adapters"),
    "002-postgres-pgvector.md": ("PostgreSQL", "pgvector"),
    "003-pluggable-model-providers.md": (
        "hermetic",
        "egress",
        "ALLOW_HOSTED_PROVIDERS",
    ),
    "004-deterministic-scoring.md": ("score", "domain", "span"),
    "005-provider-selection-as-runtime-state.md": (
        "workspace",
        "runtime",
        "never returns a key",
    ),
    "006-tanstack-start-frontend.md": ("TanStack Start", "proxy"),
    "007-grounded-generation.md": ("validator", "cited spans", "hermetic"),
}

REQUIRED_THREAT_TOPICS = (
    "upload",
    "document text",
    "job-description",
    "model output",
    "generated draft",
    "personal data",
    "egress",
)

REQUIRED_SCENARIOS = {
    "clean_match",
    "partial_match",
    "poor_match",
    "vague_seniority",
    "injection_attempt",
    "recency_decay",
}

DATASET_CASE_KEYS = {
    "id",
    "cv_id",
    "job_id",
    "expected_requirements",
    "expected_absent",
    "expected_mapping",
    "expected_reasons",
    "questions",
    "generation_probes",
}


def test_agents_and_features_share_the_invariant() -> None:
    agents = AGENTS.read_text(encoding="utf-8")
    features = FEATURES.read_text(encoding="utf-8")
    assert INVARIANT in agents
    assert INVARIANT in features


def test_agents_records_product_scope_boundaries() -> None:
    agents = AGENTS.read_text(encoding="utf-8")
    assert "## Product scope" in agents
    for anchor in (
        "candidate's tool",
        "One CV per workspace",
        "No scanned-image",
        "No authentication",
        "generated drafts",
        "docs/features.md",
    ):
        assert anchor in agents, f"AGENTS.md missing scope anchor: {anchor}"


def test_adrs_001_to_007_exist_and_state_the_fixed_direction() -> None:
    missing: list[str] = []
    for name, needles in REQUIRED_ADRS.items():
        path = ADR_DIR / name
        if not path.is_file():
            missing.append(f"{name}: absent")
            continue
        text = path.read_text(encoding="utf-8")
        assert "- Status: accepted" in text, f"{name} must be accepted"
        for needle in needles:
            assert needle.lower() in text.lower(), f"{name} missing {needle!r}"
    assert missing == [], "; ".join(missing)


def test_threat_model_names_required_trust_boundaries() -> None:
    text = THREAT_MODEL.read_text(encoding="utf-8").lower()
    assert "## Trust boundaries" in THREAT_MODEL.read_text(encoding="utf-8")
    for topic in REQUIRED_THREAT_TOPICS:
        assert topic.lower() in text, f"threat-model.md missing topic: {topic}"


def test_fixture_manifest_covers_required_scenarios() -> None:
    assert MANIFEST.is_file(), "sample-data/fixtures/manifest.json is required"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    resumes = list((FIXTURES / "resumes").glob("cv-*.txt"))
    jobs = list((FIXTURES / "job-descriptions").glob("jd-*.txt"))
    assert {p.name for p in resumes} == set(manifest["cvs"]), "undeclared CV fixture"
    assert {p.name for p in jobs} == set(manifest["jobs"]), "undeclared JD fixture"
    scenarios = {entry["scenario"] for entry in manifest["pairings"]}
    assert scenarios == REQUIRED_SCENARIOS
    for entry in manifest["pairings"]:
        cv = FIXTURES / "resumes" / entry["cv"]
        jd = FIXTURES / "job-descriptions" / entry["job"]
        assert cv.is_file(), f"missing CV {cv.name}"
        assert jd.is_file(), f"missing JD {jd.name}"
        assert "synthetic" in cv.read_text(encoding="utf-8").lower()
        assert "synthetic" in jd.read_text(encoding="utf-8").lower()


def test_injection_fixture_contains_an_instruction_attempt() -> None:
    path = FIXTURES / "job-descriptions" / "jd-injection-attempt.txt"
    text = path.read_text(encoding="utf-8").lower()
    assert "ignore" in text and "instruction" in text


def test_recency_cv_contains_dated_experience() -> None:
    path = FIXTURES / "resumes" / "cv-dated-experience.txt"
    text = path.read_text(encoding="utf-8")
    assert "2014" in text or "2015" in text
    assert "2023" in text or "2024" in text


def test_evaluation_dataset_stub_matches_documented_shape() -> None:
    assert DATASET.is_file()
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    assert "version" in payload
    assert "cases" in payload and isinstance(payload["cases"], list)
    assert len(payload["cases"]) >= 1
    case = payload["cases"][0]
    missing = DATASET_CASE_KEYS - set(case)
    assert missing == set(), f"dataset case missing keys: {sorted(missing)}"
    doc = EVALUATION.read_text(encoding="utf-8")
    for field in (
        "expected_requirements",
        "expected_mapping",
        "generation_probes",
        "citation_validity_rate",
    ):
        assert field in doc


def test_scoring_rubric_is_configuration_matching_features() -> None:
    assert RUBRIC.is_file(), "config/scoring_rubric.toml must hold starting weights"
    rubric = tomllib.loads(RUBRIC.read_text(encoding="utf-8"))
    assert rubric["weights"]["must_have"] == 3
    assert rubric["weights"]["desirable"] == 1
    assert rubric["status"]["met"] == 1.0
    assert rubric["status"]["partial"] == 0.5
    assert rubric["status"]["missing"] == 0.0
    assert rubric["recency"]["within_2y"] == 1.0
    assert rubric["recency"]["from_2y_to_5y"] == 0.85
    assert rubric["recency"]["over_5y"] == 0.7
    assert rubric["bands"]["strong_match_min"] == 75
    assert rubric["bands"]["partial_match_min"] == 50
    assert rubric["mapping"]["similarity_floor"] == 0.55
    features = FEATURES.read_text(encoding="utf-8")
    assert "must-have = 3" in features
    assert "configuration" in features.lower()
    assert "initial" in features.lower()
