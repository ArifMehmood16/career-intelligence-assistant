"""The boundary is only real if the build fails when it is crossed.

AGENTS.md: domain/ and application/ must not import a web framework, an ORM or a
provider SDK. This test is what makes that a rule rather than an intention.
"""

import ast
from pathlib import Path

FORBIDDEN = {
    "fastapi",
    "starlette",
    "sqlalchemy",
    "alembic",
    "psycopg",
    "httpx",
    "requests",
    "openai",
    "anthropic",
    "ollama",
}

GUARDED = ("domain", "application")

SRC = Path(__file__).resolve().parents[2] / "src" / "career_assistant"


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_guarded_layers_import_no_framework_or_sdk() -> None:
    offences: list[str] = []

    for layer in GUARDED:
        for module in (SRC / layer).rglob("*.py"):
            crossed = _imported_roots(module) & FORBIDDEN
            if crossed:
                offences.append(f"{module.relative_to(SRC)}: {sorted(crossed)}")

    assert offences == [], "framework or SDK imports in a guarded layer: " + "; ".join(
        offences
    )


def test_the_guard_can_fail(tmp_path: Path) -> None:
    """A guard nobody has seen fail is not a guard."""
    offender = tmp_path / "offender.py"
    offender.write_text("import sqlalchemy\n", encoding="utf-8")

    assert _imported_roots(offender) & FORBIDDEN == {"sqlalchemy"}
