"""Phase 13A.9 — production wiring matrix must name every live HTTP route.

An isolated domain or repository test is not a wired feature. This suite fails when
the README still describes an earlier phase, or when a FastAPI route is missing from
docs/production-wiring.md.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.routing import APIRoute

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
)


def _live_api_routes() -> list[str]:
    app = create_app()
    found: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api"):
            continue
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            found.append(f"{method} {route.path}")
    return sorted(set(found))


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


def test_readme_status_matches_observed_phase_13a_behaviour() -> None:
    text = README.read_text(encoding="utf-8")
    for claim in STALE_README_CLAIMS:
        assert claim not in text, f"README still claims {claim!r}"
    assert "docs/production-wiring.md" in text


def test_production_wiring_matrix_covers_every_live_api_route() -> None:
    assert WIRING.is_file(), "docs/production-wiring.md is required"
    text = WIRING.read_text(encoding="utf-8")
    assert "| Route | Use case | Provider resolver | SQL adapter |" in text
    documented = {row[0] for row in _matrix_rows(text) if row}
    missing = [route for route in _live_api_routes() if route not in documented]
    assert missing == [], (
        "production-wiring.md missing routes: " + ", ".join(missing)
    )
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
    assert "docs/production-wiring.md" in contract
    assert "Phase 12 updates the existing frontend types" not in contract
