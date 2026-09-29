"""The hermetic structured fixture keeps v2 tests offline (PLAN 18.4).

It is a test fixture, not a product default: rules good enough to exercise the
pipeline on the synthetic fixtures, never presented as model quality.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.application.chunking.service import (
    ChunkingRequest,
    DocumentChunker,
)
from career_assistant.application.contracts.judge import JudgeResponse
from career_assistant.application.ports.errors import ProviderUnavailableError
from career_assistant.application.ports.structured import StructuredRequest
from career_assistant.domain.documents import DocumentKind

FIXTURES = Path(__file__).resolve().parents[3] / "sample-data" / "fixtures"
CVS = sorted((FIXTURES / "resumes").glob("*.txt"))
JDS = sorted((FIXTURES / "job-descriptions").glob("*.txt"))


def _chunk(kind: DocumentKind, text: str):  # noqa: ANN202
    chunker = DocumentChunker(HermeticStructuredCompleter())
    return chunker.chunk(ChunkingRequest(document_id="d", kind=kind, text=text))


@pytest.mark.parametrize("path", CVS, ids=[p.stem for p in CVS])
def test_every_synthetic_cv_chunks_without_a_repair(path: Path) -> None:
    outcome = _chunk(DocumentKind.CV, path.read_text(encoding="utf-8"))

    assert outcome.repairs == 0
    assert outcome.provider_id == "hermetic"
    assert any(c.kind == "experience" for c in outcome.chunks)


@pytest.mark.parametrize("path", JDS, ids=[p.stem for p in JDS])
def test_every_synthetic_advert_chunks_without_a_repair(path: Path) -> None:
    outcome = _chunk(DocumentKind.JOB_DESCRIPTION, path.read_text(encoding="utf-8"))

    assert outcome.repairs == 0
    assert any(c.atomic_requirements for c in outcome.chunks)


def test_a_role_heading_and_its_bullets_are_linked() -> None:
    text = (
        "EXPERIENCE\n"
        "Cedar Metrics Co — BI Analyst\n"
        "June 2021 – Present\n"
        "- Built Power BI dashboards for support SLAs\n"
        "and ticket volume.\n"
    )

    chunks = _chunk(DocumentKind.CV, text).chunks

    assert [(c.first_line, c.last_line, c.kind) for c in chunks] == [
        (1, 1, "other"),
        (2, 3, "role_heading"),
        (4, 5, "experience"),
    ]
    assert chunks[2].role_ref == 2


def test_contact_lines_are_contact_and_never_evidence() -> None:
    text = "Jane Doe\nEmail: jane@example.com\nSKILLS\nPython, SQL\n"

    chunks = _chunk(DocumentKind.CV, text).chunks

    assert [c.kind for c in chunks] == ["contact", "contact", "other", "skills"]
    assert not any(c.evidence_eligible for c in chunks[:2])
    assert [t.surface for t in chunks[3].tech_terms] == ["Python", "SQL"]


def test_an_instruction_in_an_advert_is_not_a_requirement() -> None:
    text = (FIXTURES / "job-descriptions" / "jd-injection-attempt.txt").read_text(
        encoding="utf-8"
    )

    chunks = _chunk(DocumentKind.JOB_DESCRIPTION, text).chunks

    quotes = [r.quote for c in chunks for r in c.atomic_requirements]
    assert not any("IGNORE" in q or "CUDA" in q for q in quotes)
    desirable = [
        r for c in chunks for r in c.atomic_requirements if "Looker" in r.quote
    ]
    assert desirable and desirable[0].must_have is False


def test_the_fixture_is_deterministic() -> None:
    text = CVS[0].read_text(encoding="utf-8")

    assert _chunk(DocumentKind.CV, text) == _chunk(DocumentKind.CV, text)


def test_a_contract_with_no_fixture_is_refused() -> None:
    with pytest.raises(ProviderUnavailableError):
        HermeticStructuredCompleter().complete_structured(
            StructuredRequest(
                contract=JudgeResponse, system="s", user="u", max_output_tokens=10
            )
        )
