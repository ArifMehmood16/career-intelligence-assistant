"""Hosted analysis overlaps calls that do not need each other's replies.

A local or hermetic model stays one call at a time. Repairs still follow the
reply they correct, and a later section is validated only after earlier headings
exist.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from tests.support.in_memory_index import InMemoryIndexStore
from tests.support.in_memory_verdicts import InMemoryVerdictCache
from tests.support.index_backed_search import IndexBackedSearch

from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
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
from career_assistant.application.contracts.chunking import (
    CvChunkResponse,
    JobChunkResponse,
)
from career_assistant.application.contracts.judge import JudgeResponse
from career_assistant.application.indexing.service import DocumentIndexer
from career_assistant.application.judge.cache import ModelIdentity
from career_assistant.application.judge.matching import (
    CandidateSearchResult,
    EvidenceMatcher,
)
from career_assistant.application.judge.prompt import JudgeLimits
from career_assistant.application.judge.service import RequirementJudge
from career_assistant.application.ports.structured import (
    StructuredRequest,
    StructuredResult,
)
from career_assistant.application.ports.types import CapabilityDescriptor
from career_assistant.application.providers.execution import ExecutionProfile
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric_v2
from career_assistant.domain.candidate_facts import CandidateFacts
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.judging import Candidate, RequirementPacket
from career_assistant.domain.search import SearchHit

ROOT = Path(__file__).resolve().parents[3]
RUBRIC = load_scoring_rubric_v2(ROOT / "config" / "scoring_rubric.toml")
AS_OF = date(2026, 9, 1)
FACTS = CandidateFacts(terms=(), roles=())
WIDE = (
    "EXPERIENCE\nSenior Engineer, Acme, 2019 – 2024\n"
    "- Led a migration.\nSKILLS\nPython\n"
)
_IDS = re.compile(r'id="([^"]+)"')
_REPAIR = "broke these rules"


class HoldingPort:
    """Blocks a wave of calls until every party is inside one."""

    def __init__(
        self,
        *,
        leaves_machine: bool,
        parties: int = 2,
        context_window_tokens: int = 1_400,
        max_output_tokens: int = 160,
        gate: Callable[[str], bool] | None = None,
    ) -> None:
        self.leaves_machine = leaves_machine
        self.peak = 0
        self.calls = 0
        self.repair_followed_its_reply = False
        self._in_flight = 0
        self._lock = threading.Lock()
        self._done: set[str] = set()
        self._gate = gate
        self._barrier = (
            threading.Barrier(parties, timeout=2) if leaves_machine else None
        )
        self.context_window_tokens = context_window_tokens
        self.max_output_tokens = max_output_tokens

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="scripted",
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=self.context_window_tokens,
            max_output_tokens=self.max_output_tokens,
            embedding_dimensions=None,
            leaves_machine=self.leaves_machine,
            execution=ExecutionProfile(
                completion_concurrency=4 if self.leaves_machine else 1
            ),
        )

    def complete_structured[T](
        self, request: StructuredRequest[T]
    ) -> StructuredResult[T]:
        repair = _REPAIR in request.user
        with self._lock:
            self._in_flight += 1
            self.peak = max(self.peak, self._in_flight)
            self.calls += 1
            if repair:
                ids = _requirement_ids(request.user)
                self.repair_followed_its_reply = all(i in self._done for i in ids)
        if self._barrier is not None and self._should_wait(request.user, repair):
            self._barrier.wait()
        try:
            value = _reply(request)
            return StructuredResult(
                value=value,
                provider_id="scripted",
                model_tag="scripted-v1",
                left_machine=self.leaves_machine,
                attempts=1,
                input_tokens=10,
                output_tokens=10,
            )
        finally:
            with self._lock:
                self._in_flight -= 1
                if not repair:
                    self._done.update(_requirement_ids(request.user))

    def _should_wait(self, user: str, repair: bool) -> bool:
        if repair:
            return False
        return self._gate is None or self._gate(user)


def _requirement_ids(user: str) -> tuple[str, ...]:
    seen: list[str] = []
    for requirement_id in _IDS.findall(user):
        if requirement_id not in seen:
            seen.append(requirement_id)
    return tuple(seen)


def _reply[T](request: StructuredRequest[T]) -> T:
    contract = request.contract
    if contract is JudgeResponse:
        if "Has run vector search." in request.user:
            verdicts = [
                _rewrite_verdict(requirement_id, request.user)
                for requirement_id in _requirement_ids(request.user)
            ]
        else:
            bad = _REPAIR not in request.user
            verdicts = [
                _verdict(requirement_id, paraphrased=bad and requirement_id == "r-bad")
                for requirement_id in _requirement_ids(request.user)
            ]
        return contract.model_validate({"verdicts": verdicts})
    if contract is CvChunkResponse:
        return contract.model_validate(_cv_body(request.user))
    if contract is JobChunkResponse:
        return contract.model_validate(
            {"chunks": [{"first_line": 1, "last_line": 1, "kind": "other"}]}
        )
    raise AssertionError(contract)


def _cv_body(user: str) -> dict[str, object]:
    if "L4:" in user:
        return {
            "chunks": [
                {
                    "first_line": 4,
                    "last_line": 5,
                    "kind": "experience",
                    "role_ref": 2,
                }
            ]
        }
    if "L2:" in user:
        return {
            "chunks": [
                {"first_line": 1, "last_line": 1, "kind": "other"},
                {"first_line": 2, "last_line": 2, "kind": "role_heading"},
                {"first_line": 3, "last_line": 3, "kind": "experience", "role_ref": 2},
            ]
        }
    return {"chunks": [{"first_line": 1, "last_line": 1, "kind": "contact"}]}


def _verdict(requirement_id: str, *, paraphrased: bool) -> dict[str, object]:
    quote = "built pgvector search" if paraphrased else "pgvector"
    return {
        "requirement_id": requirement_id,
        "verdict": "met",
        "match": {
            "score": 3,
            "rationale": "Built it.",
            "evidence": [{"chunk_id": f"c-{requirement_id}", "quote": quote}],
        },
        "retrieval_feedback": {"sufficient": True},
    }


def _rewrite_verdict(requirement_id: str, user: str) -> dict[str, object]:
    if "Shipped semantic search." in user:
        return {
            "requirement_id": requirement_id,
            "verdict": "met",
            "match": {
                "score": 3,
                "rationale": "Shipped it.",
                "evidence": [{"chunk_id": "c-delivery", "quote": "semantic search"}],
            },
            "retrieval_feedback": {"sufficient": True},
        }
    return {
        "requirement_id": requirement_id,
        "verdict": "partial",
        "match": {
            "score": 2,
            "rationale": "Only a skills line.",
            "evidence": [{"chunk_id": "c-skills", "quote": "pgvector"}],
        },
        "retrieval_feedback": {
            "sufficient": False,
            "rewrite_query": f"{requirement_id} again",
        },
    }


def _packet(requirement_id: str) -> RequirementPacket:
    return RequirementPacket(
        requirement_id=requirement_id,
        quote="Vector databases",
        statement="Has used a vector database.",
        must_have=True,
        terms=("pgvector",),
        candidates=(
            Candidate(
                f"c-{requirement_id}", "experience", "cv", "Built it on pgvector."
            ),
        ),
    )


def test_hosted_section_calls_overlap_and_a_later_role_ref_still_resolves() -> None:
    port = HoldingPort(
        leaves_machine=True,
        context_window_tokens=1_645,
        max_output_tokens=8_000,
        gate=lambda user: "<document>" in user,
    )
    request = ChunkingRequest(document_id="cv-1", kind=DocumentKind.CV, text=WIDE)

    outcome = DocumentChunker(port).chunk(request)

    assert port.peak == 2
    assert port.calls == 2
    later = next(chunk for chunk in outcome.chunks if chunk.first_line == 4)
    assert later.role_ref == 2


def test_a_local_model_chunks_sections_one_at_a_time() -> None:
    port = HoldingPort(
        leaves_machine=False, context_window_tokens=1_645, max_output_tokens=8_000
    )
    request = ChunkingRequest(document_id="cv-1", kind=DocumentKind.CV, text=WIDE)

    outcome = DocumentChunker(port).chunk(request)

    assert port.peak == 1
    assert port.calls == 2
    assert [chunk.first_line for chunk in outcome.chunks] == [1, 2, 3, 4]


def test_hosted_judge_batches_overlap_and_progress_stays_monotonic() -> None:
    port = HoldingPort(
        leaves_machine=True, max_output_tokens=400, context_window_tokens=32_768
    )
    judged: list[int] = []
    judge = _judge(port)

    outcome = judge.judge(
        [_packet("r1"), _packet("r2")],
        FACTS,
        as_of=AS_OF,
        on_judged=judged.append,
    )

    assert port.peak == 2
    assert set(outcome.verdicts) == {"r1", "r2"}
    assert judged == sorted(judged)
    assert judged[-1] == 2


def test_a_local_model_judges_batches_one_at_a_time() -> None:
    port = HoldingPort(
        leaves_machine=False, max_output_tokens=400, context_window_tokens=32_768
    )

    outcome = _judge(port).judge([_packet("r1"), _packet("r2")], FACTS, as_of=AS_OF)

    assert port.peak == 1
    assert set(outcome.verdicts) == {"r1", "r2"}


def test_a_repair_starts_only_after_its_own_batch_replied() -> None:
    port = HoldingPort(
        leaves_machine=True, max_output_tokens=400, context_window_tokens=32_768
    )

    outcome = _judge(port).judge([_packet("r-bad"), _packet("r2")], FACTS, as_of=AS_OF)

    assert port.calls == 3
    assert port.repair_followed_its_reply
    assert outcome.incomplete == ()


def test_hosted_indexing_overlaps_the_cv_and_the_advert() -> None:
    port = _wide(leaves_machine=True)

    analysis = _analysis(port).run(_documents())

    assert port.peak == 2
    assert port.calls == 2
    assert analysis.requirements == ()


def test_a_local_model_indexes_the_cv_before_the_advert() -> None:
    port = _wide(leaves_machine=False)

    _analysis(port).run(_documents())

    assert port.peak == 1
    assert port.calls == 2


def test_hosted_rewrites_share_one_rejudge_and_embedding_batch() -> None:
    port = _wide(leaves_machine=True, gate=lambda user: False)
    delivery = Candidate("c-delivery", "experience", "cv", "Shipped semantic search.")
    search = _RewriteSearch(delivery)

    EvidenceMatcher(search, _judge(port), max_rewrites=5).match(
        [_rewrite_requirement("r1"), _rewrite_requirement("r2")],
        FACTS,
        as_of=AS_OF,
    )

    assert port.peak == 1
    assert port.calls == 2
    assert search.batches[0] == ("Has run vector search.", "Has run vector search.")
    assert search.batches[1] == ("r1 again", "r2 again")


def test_a_local_model_rejudges_requirements_in_one_batch() -> None:
    port = _wide(leaves_machine=False)
    delivery = Candidate("c-delivery", "experience", "cv", "Shipped semantic search.")
    search = _RewriteSearch(delivery)

    EvidenceMatcher(search, _judge(port), max_rewrites=5).match(
        [_rewrite_requirement("r1"), _rewrite_requirement("r2")],
        FACTS,
        as_of=AS_OF,
    )

    assert port.peak == 1
    assert port.calls == 2
    assert search.batches[1] == ("r1 again", "r2 again")


def _wide(
    *, leaves_machine: bool, gate: Callable[[str], bool] | None = None
) -> HoldingPort:
    return HoldingPort(
        leaves_machine=leaves_machine,
        context_window_tokens=32_768,
        max_output_tokens=8_000,
        gate=gate,
    )


def _judge(port: HoldingPort) -> RequirementJudge:
    return RequirementJudge(
        port,
        InMemoryVerdictCache(),
        ModelIdentity("scripted", "scripted-v1"),
        JudgeLimits(),
    )


def _documents() -> V2Documents:
    return V2Documents(
        workspace_id="ws-1",
        cv=ChunkingRequest(document_id="cv-1", kind=DocumentKind.CV, text="Jane Doe\n"),
        advert=ChunkingRequest(
            document_id="jd-1",
            kind=DocumentKind.JOB_DESCRIPTION,
            text="Need Python\n",
        ),
        as_of=AS_OF,
    )


def _analysis(port: HoldingPort) -> RoleAnalysisV2:
    store = InMemoryIndexStore()
    embedding = HermeticEmbeddingAdapter()
    return RoleAnalysisV2(
        indexer=DocumentIndexer(
            chunker=DocumentChunker(port),
            embedding=embedding,
            store=store,
            max_chars_per_text=8_000,
        ),
        judge=_judge(port),
        embedding=embedding,
        search=IndexBackedSearch(
            store,
            "ws-1",
            {"cv-1": DocumentKind.CV, "jd-1": DocumentKind.JOB_DESCRIPTION},
        ),
        rubric=RUBRIC,
        limits=V2Limits(max_rewrites=5, max_chars_per_text=8_000),
    )


class _RewriteSearch:
    def __init__(self, extra: Candidate) -> None:
        self._extra = extra
        self.batches: list[tuple[str, ...]] = []

    def find(
        self, requirement: RequirementPacket, query_text: str
    ) -> CandidateSearchResult:
        return self.find_all([(requirement, query_text)])[0]

    def find_all(
        self, items: Sequence[tuple[RequirementPacket, str]]
    ) -> tuple[CandidateSearchResult, ...]:
        texts = tuple(text for _, text in items)
        self.batches.append(texts)
        if texts and texts[0].endswith("again"):
            return tuple(_hit(self._extra) for _ in items)
        skills = Candidate("c-skills", "skills", "cv", "Python, pgvector")
        return tuple(_hit(skills) for _ in items)


def _hit(candidate: Candidate) -> CandidateSearchResult:
    hit = SearchHit(candidate.chunk_id, 0.5, 1, None, None)
    return CandidateSearchResult(hits=(hit,), candidates=(candidate,))


def _rewrite_requirement(requirement_id: str) -> RequirementPacket:
    return RequirementPacket(
        requirement_id=requirement_id,
        quote="Vector search",
        statement="Has run vector search.",
        must_have=True,
        terms=("pgvector",),
        candidates=(),
    )
