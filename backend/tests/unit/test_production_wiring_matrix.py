"""Phase 13A.9 — production wiring matrix must name every live HTTP route.

An isolated domain or repository test is not a wired feature. This suite fails when
the README still describes an earlier phase, or when a FastAPI route is missing from
docs/production-wiring.md.
"""

from __future__ import annotations

from pathlib import Path

from career_assistant.main import create_app

ROOT = Path(__file__).resolve().parents[3]
README = ROOT / "README.md"
WIRING = ROOT / "docs" / "production-wiring.md"
THREAT_MODEL = ROOT / "docs" / "threat-model.md"
API_CONTRACT = ROOT / "docs" / "api-contract.md"

STALE_README_CLAIMS = (
    "phase 10 generation complete",
    "HTTP routes are next with Phase 11",
    "serving the Lovable screens against fixture data",
    "has not been built yet",
    "not a process restart",
    "Default runs are hermetic: lexical embeddings and a rule-based extractor",
    "`hermetic` (default)",
    "waits on the rest of 13C (output depth)",
)

ADR_010 = ROOT / "docs" / "adr" / "010-model-first-extraction.md"
FEATURES = ROOT / "docs" / "features.md"


def _live_api_routes() -> list[str]:
    spec = create_app().openapi()
    found: list[str] = []
    for path, operations in spec["paths"].items():
        if not path.startswith("/api"):
            continue
        for method, _op in operations.items():
            if method.upper() not in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
                continue
            found.append(f"{method.upper()} {path}")
    routes = sorted(set(found))
    if len(routes) < 20:
        raise AssertionError(
            f"expected at least 20 /api routes, found {len(routes)}: {routes}"
        )
    return routes


def _matrix_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or cells[0] in {"Route", "---"} or set(cells[0]) <= {"-"}:
            continue
        rows.append(cells)
    return rows


def test_readme_status_matches_observed_phase_13c_behaviour() -> None:
    text = README.read_text(encoding="utf-8")
    for claim in STALE_README_CLAIMS:
        assert claim not in text, f"README still claims {claim!r}"
    assert "docs/production-wiring.md" in text
    assert "docs/adr/010-model-first-extraction.md" in text
    assert "`hermetic` (test fixture)" in text
    assert "`ollama` (product default)" in text


def test_adr_010_records_the_audit_and_closed_13c_work() -> None:
    assert ADR_010.is_file(), "ADR 010 is required by PLAN 13C.10"
    text = ADR_010.read_text(encoding="utf-8")
    assert "verbatim" in text.lower()
    assert "item_type" in text
    assert "Output-depth work remains PLAN 13C.8" not in text
    assert "13C.5" in text
    assert "13C.8" in text


def test_features_and_threat_model_state_the_scoring_boundary() -> None:
    features = FEATURES.read_text(encoding="utf-8")
    threat = THREAT_MODEL.read_text(encoding="utf-8").lower()
    assert "unscored" in features
    assert "benefit" in features
    assert "logistics" in features
    assert "item_type" in threat or "benefit" in threat
    assert "salary" in threat or "logistics" in threat


def test_production_wiring_matrix_covers_every_live_api_route() -> None:
    assert WIRING.is_file(), "docs/production-wiring.md is required"
    text = WIRING.read_text(encoding="utf-8")
    assert "| Route | Use case | Provider resolver | SQL adapter |" in text
    documented = {row[0] for row in _matrix_rows(text) if row}
    missing = [route for route in _live_api_routes() if route not in documented]
    assert missing == [], "production-wiring.md missing routes: " + ", ".join(missing)
    extras = sorted(
        route
        for route in documented
        if route.startswith(("GET ", "POST ", "PUT ", "DELETE ", "PATCH "))
        and route not in _live_api_routes()
    )
    assert extras == [], (
        "production-wiring.md lists routes that are not live: " + ", ".join(extras)
    )
    for row in _matrix_rows(text):
        assert len(row) >= 4, f"incomplete matrix row: {row!r}"
        assert all(cell for cell in row[:4]), f"empty matrix cell: {row!r}"


def test_threat_model_and_api_contract_name_production_sql_wiring() -> None:
    threat = THREAT_MODEL.read_text(encoding="utf-8").lower()
    assert "create_app()" in THREAT_MODEL.read_text(encoding="utf-8")
    assert "in-memory" in threat
    assert "postgresql" in threat
    contract = API_CONTRACT.read_text(encoding="utf-8")
    assert "production-wiring.md" in contract
    assert "Phase 12 updates the existing frontend types" not in contract
