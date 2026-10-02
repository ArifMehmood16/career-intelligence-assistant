"""Named synthetic inputs for PLAN 19.4; no arbitrary document paths."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "sample-data/fixtures"


class _Pairing(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    cv: str
    job: str


class _Manifest(BaseModel):
    version: Literal[1]
    pairings: tuple[_Pairing, ...] = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    case_id: str
    cv_text: str
    jd_text: str
    cv_sha256: str
    jd_sha256: str


@dataclass(frozen=True, slots=True)
class BenchmarkDataset:
    manifest_sha256: str
    cases: tuple[BenchmarkCase, ...]


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture(directory: str, name: str) -> bytes:
    if re.fullmatch(r"[a-z0-9-]+\.txt", name) is None:
        raise ValueError("invalid_fixture_name")
    root = (FIXTURES / directory).resolve()
    if root.parent != FIXTURES.resolve():
        raise ValueError("fixture_directory_escapes_root")
    path = (root / name).resolve()
    if path.parent != root:
        raise ValueError("fixture_path_escapes_root")
    return path.read_bytes()


def load_dataset(selected: Sequence[str] = ()) -> BenchmarkDataset:
    raw = (FIXTURES / "manifest.json").read_bytes()
    manifest = _Manifest.model_validate_json(raw)
    pairings = {pair.id: pair for pair in manifest.pairings}
    if len(pairings) != len(manifest.pairings):
        raise ValueError("duplicate_case_id")
    wanted = tuple(dict.fromkeys(selected)) if selected else tuple(pairings)
    if any(name not in pairings for name in wanted):
        raise ValueError("unknown_case")
    cases: list[BenchmarkCase] = []
    for name in wanted:
        pair = pairings[name]
        cv = _fixture("resumes", pair.cv)
        jd = _fixture("job-descriptions", pair.job)
        cases.append(
            BenchmarkCase(
                name,
                cv.decode("utf-8"),
                jd.decode("utf-8"),
                fingerprint(cv),
                fingerprint(jd),
            )
        )
    return BenchmarkDataset(fingerprint(raw), tuple(cases))
