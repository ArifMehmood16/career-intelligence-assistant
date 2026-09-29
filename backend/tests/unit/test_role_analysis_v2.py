"""PLAN 18.10 — one v2 analysis indexes, matches and scores a role end to end.

Hermetic chunking, taxonomy, judging and embeddings, with the in-memory index and
search. The judge may refuse; then nothing is scored.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from tests.support.in_memory_index import InMemoryIndexStore
from tests.support.in_memory_verdicts import InMemoryVerdictCache
from tests.support.index_backed_search import IndexBackedSearch
from tests.support.recording_progress import RecordingProgress
from tests.support.refusing_structured import RefusingJudge

from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.application.analysis.v2 import (
    RoleAnalysisV2,
    V2Documents,
    V2Limits,
)
from career_assistant.application.chunking.service import (
    ChunkingRequest,
    DocumentChunker,
)
from career_assistant.application.graph.taxonomy import TermTaxonomist
from career_assistant.application.indexing.service import DocumentIndexer
from career_assistant.application.judge.cache import ModelIdentity
from career_assistant.application.judge.prompt import JudgeLimits
from career_assistant.application.judge.service import RequirementJudge
from career_assistant.application.ports.structured import StructuredCompletionPort
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric_v2
from career_assistant.domain.documents import DocumentKind

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "sample-data" / "fixtures"
RUBRIC = load_scoring_rubric_v2(ROOT / "config" / "scoring_rubric.toml")
WS = "ws-1"
AS_OF = date(2026, 9, 1)


def _documents() -> V2Documents:
    cv = (FIXTURES / "resumes" / "cv-strong-match.txt").read_text(encoding="utf-8")
    jd = (FIXTURES / "job-descriptions" / "jd-clean-match.txt").read_text(
        encoding="utf-8"
    )
    return V2Documents(
        workspace_id=WS,
        cv=ChunkingRequest(document_id="cv-1", kind=DocumentKind.CV, text=cv),
        advert=ChunkingRequest(
            document_id="jd-1", kind=DocumentKind.JOB_DESCRIPTION, text=jd
        ),
        as_of=AS_OF,
    )


def _analysis(structured: StructuredCompletionPort) -> RoleAnalysisV2:
    store = InMemoryIndexStore()
    embedding = HermeticEmbeddingAdapter()
    return RoleAnalysisV2(
        indexer=DocumentIndexer(
            chunker=DocumentChunker(structured),
            taxonomist=TermTaxonomist(structured),
            embedding=embedding,
            store=store,
            max_chars_per_text=8_000,
        ),
        judge=RequirementJudge(
            structured,
            InMemoryVerdictCache(),
            ModelIdentity("hermetic", "rules-v1"),
            JudgeLimits(),
        ),
        embedding=embedding,
        search=IndexBackedSearch(
            store,
            WS,
            {"cv-1": DocumentKind.CV, "jd-1": DocumentKind.JOB_DESCRIPTION},
        ),
        rubric=RUBRIC,
        limits=V2Limits(max_rewrites=5, max_chars_per_text=8_000),
    )


def test_every_advert_requirement_is_judged_and_scored() -> None:
    analysis = _analysis(HermeticStructuredCompleter()).run(_documents())

    ids = {r.packet.requirement_id for r in analysis.requirements}
    assert ids
    assert set(analysis.match.verdicts) == ids
    assert set(analysis.match.traces) == ids
    assert analysis.fit.publishable
    assert analysis.fit.score is not None
    assert {c.requirement_id for c in analysis.fit.components} == ids
    assert not analysis.left_machine


def test_requirement_ids_are_stable_for_the_same_stored_advert() -> None:
    analysis = _analysis(HermeticStructuredCompleter())

    first = analysis.run(_documents())
    second = analysis.run(_documents())

    assert [r.packet.requirement_id for r in first.requirements] == [
        r.packet.requirement_id for r in second.requirements
    ]


def test_a_refusing_judge_leaves_the_analysis_unscored() -> None:
    analysis = _analysis(RefusingJudge()).run(_documents())

    assert analysis.requirements
    assert analysis.match.incomplete
    assert not analysis.fit.publishable
    assert analysis.fit.score is None
    assert analysis.gaps == ()


def test_progress_walks_the_v2_tasks_in_order() -> None:
    progress = RecordingProgress()

    analysis = _analysis(HermeticStructuredCompleter()).run(
        _documents(), progress=progress
    )

    entered = progress.entered
    assert entered[:4] == ["read_cv", "read_advert", "search", "judge"]
    assert entered[-1] == "score"
    assert ("skip", "recheck") in progress.events or "recheck" in entered
    total = len(analysis.requirements)
    assert ("judge", total, total) in progress.events
