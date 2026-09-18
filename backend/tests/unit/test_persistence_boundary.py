"""Phase 4.5 — SQLAlchemy stays behind the adapter boundary."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "career_assistant"
ADAPTERS = SRC / "adapters"
PERSISTENCE = ADAPTERS / "persistence"


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_sqlalchemy_only_imported_under_adapters_persistence() -> None:
    offences: list[str] = []
    for module in SRC.rglob("*.py"):
        if PERSISTENCE in module.parents or module.parent == PERSISTENCE:
            continue
        # Alembic env lives with migrations, outside the package import graph of
        # domain/application, but must not be imported from application code.
        if "migrations" in module.parts:
            continue
        roots = _imported_roots(module)
        if "sqlalchemy" in roots or "alembic" in roots:
            offences.append(str(module.relative_to(SRC)))
    assert offences == [], (
        "SQLAlchemy/Alembic escaped adapters/persistence: " + ", ".join(offences)
    )


def test_persistence_adapter_package_exists() -> None:
    assert PERSISTENCE.is_dir(), "adapters/persistence must exist for Phase 4"
    assert (PERSISTENCE / "__init__.py").is_file()
