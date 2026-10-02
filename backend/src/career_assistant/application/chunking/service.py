"""Extract complete document chunks in one call and validate every cited field.

Input limits split before the call. Actual truncation triggers bounded splits;
invalid coverage gets one repair. Independent initial calls overlap according to
adapter policy, while validation preserves global role-heading references.
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from dataclasses import dataclass, field

from career_assistant.application.chunking.mapping import proposals_from_chunks
from career_assistant.application.chunking.prompts import (
    CHUNKING_PROMPT_VERSION,
    document_system,
    document_user,
    repair_user,
)
from career_assistant.application.chunking.sections import (
    ChunkingBudget,
    plan_sections,
    section_input_tokens,
)
from career_assistant.application.contracts.chunking import (
    CoverLetterChunkResponse,
    CvChunkResponse,
    DocumentChunkResponse,
    JobChunkResponse,
)
from career_assistant.application.contracts.taxonomy import TermRelations
from career_assistant.application.graph.taxonomy import edges_from_relations
from career_assistant.application.ports.errors import (
    ProviderInputTooLargeError,
    StructuredOutputInvalidError,
    StructuredOutputTruncatedError,
)
from career_assistant.application.ports.progress import plan_calls
from career_assistant.application.ports.structured import (
    StructuredCompletionPort,
    StructuredRequest,
    StructuredResult,
)
from career_assistant.application.providers.fanout import map_in_order
from career_assistant.domain.chunking import (
    DEFAULT_CHUNK_LIMITS,
    Chunk,
    ChunkLimits,
    ChunkPlan,
    validate_chunk_plan,
)
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.knowledge_graph import GraphEdge
from career_assistant.domain.lines import NumberedLine, number_lines

_CONTRACTS: dict[DocumentKind, type[DocumentChunkResponse]] = {
    DocumentKind.CV: CvChunkResponse,
    DocumentKind.COVER_LETTER: CoverLetterChunkResponse,
    DocumentKind.JOB_DESCRIPTION: JobChunkResponse,
}
_LIMIT_ERRORS = (StructuredOutputTruncatedError, ProviderInputTooLargeError)


class ChunkingIncompleteError(Exception):
    """Ingestion failed. Carries a safe code and counts only."""

    def __init__(self, code: str, *, problem_count: int = 0) -> None:
        super().__init__(code)
        self.code = code
        self.problem_count = problem_count


@dataclass(frozen=True, slots=True)
class ChunkingRequest:
    document_id: str
    kind: DocumentKind
    text: str
    advert_title: str = ""


@dataclass(frozen=True, slots=True)
class ChunkingOutcome:
    chunks: tuple[Chunk, ...]
    calls: int
    repairs: int
    dropped_fields: int
    provider_id: str
    model_tag: str
    left_machine: bool
    prompt_version: str
    contract_version: str
    inferred_edges: tuple[GraphEdge, ...] = ()


@dataclass
class _Run:
    request: ChunkingRequest
    total_lines: int
    chunks: list[Chunk] = field(default_factory=list)
    taxonomy: list[TermRelations] = field(default_factory=list)
    calls: int = 0
    repairs: int = 0
    dropped_fields: int = 0
    provider_id: str = ""
    model_tag: str = ""
    left_machine: bool = False

    @property
    def headings(self) -> frozenset[int]:
        return frozenset(c.first_line for c in self.chunks if c.kind == "role_heading")

    def accept(self, plan: ChunkPlan) -> None:
        self.chunks.extend(plan.chunks)
        self.dropped_fields += plan.dropped_fields


class DocumentChunker:
    def __init__(
        self,
        structured: StructuredCompletionPort,
        *,
        limits: ChunkLimits = DEFAULT_CHUNK_LIMITS,
        max_output_tokens: int | None = None,
    ) -> None:
        self._structured = structured
        self._limits = limits
        self._max_output_tokens = max_output_tokens
        self._lock = threading.Lock()

    @property
    def hosted(self) -> bool:
        return self._structured.capabilities.leaves_machine

    @property
    def concurrency(self) -> int:
        return self._structured.capabilities.execution.completion_concurrency

    def chunk(self, request: ChunkingRequest) -> ChunkingOutcome:
        lines = number_lines(request.text)
        if not lines:
            raise ChunkingIncompleteError("empty_document")
        run = _Run(request=request, total_lines=len(lines))
        caps = self._structured.capabilities
        # Reserve a reply window without sacrificing all input to a large output cap.
        reserve = min(
            self._output_limit(), max(1, caps.context_window_tokens // 4), 512
        )
        budget = ChunkingBudget(caps.context_window_tokens - reserve)
        sections = plan_sections(lines, budget)
        if any(not budget.fits(section) for section in sections):
            raise ChunkingIncompleteError("chunking_input_too_large")
        prepared = [(section, self._user(run, section)) for section in sections]
        plan_calls(model=len(prepared))
        replies = map_in_order(
            prepared,
            lambda item: self._first_reply(run, item[0], item[1]),
            parallel=self.concurrency > 1,
            max_workers=self.concurrency,
        )
        for (section, user), reply in zip(prepared, replies, strict=True):
            self._accept(run, section, user, reply, depth=0)
        return ChunkingOutcome(
            chunks=tuple(run.chunks),
            calls=run.calls,
            repairs=run.repairs,
            dropped_fields=run.dropped_fields,
            provider_id=run.provider_id,
            model_tag=run.model_tag,
            left_machine=run.left_machine,
            prompt_version=CHUNKING_PROMPT_VERSION,
            contract_version=_CONTRACTS[request.kind].contract_version,
            inferred_edges=self._inferred_edges(run),
        )

    def _user(self, run: _Run, section: Sequence[NumberedLine]) -> str:
        return document_user(
            run.request.kind,
            section,
            total_lines=run.total_lines,
            advert_title=run.request.advert_title,
        )

    def _first_reply(
        self, run: _Run, section: Sequence[NumberedLine], user: str
    ) -> (
        DocumentChunkResponse
        | StructuredOutputTruncatedError
        | ProviderInputTooLargeError
    ):
        try:
            return self._call(run, section, user)
        except _LIMIT_ERRORS as error:
            return error

    def _accept(
        self,
        run: _Run,
        section: Sequence[NumberedLine],
        user: str,
        reply: DocumentChunkResponse
        | StructuredOutputTruncatedError
        | ProviderInputTooLargeError,
        *,
        depth: int,
    ) -> None:
        if isinstance(reply, _LIMIT_ERRORS):
            self._split(run, section, depth=depth, error=reply)
            return
        plan = self._validate(run, section, reply)
        if not plan.problems:
            run.accept(plan)
            run.taxonomy.extend(reply.taxonomy)
            return
        run.repairs += 1
        plan_calls(model=1)
        repaired = self._first_reply(
            run,
            section,
            repair_user(user, reply.model_dump_json(exclude_none=True), plan.problems),
        )
        if isinstance(repaired, _LIMIT_ERRORS):
            self._split(run, section, depth=depth, error=repaired)
            return
        plan = self._validate(run, section, repaired)
        if plan.problems:
            raise ChunkingIncompleteError(
                "chunking_incomplete", problem_count=len(plan.problems)
            )
        run.accept(plan)
        run.taxonomy.extend(repaired.taxonomy)

    def _split(
        self,
        run: _Run,
        section: Sequence[NumberedLine],
        *,
        depth: int,
        error: StructuredOutputTruncatedError | ProviderInputTooLargeError,
    ) -> None:
        if (
            len(section) < 2
            or depth >= self._structured.capabilities.execution.max_document_split_depth
        ):
            raise ChunkingIncompleteError("chunking_truncated") from error
        half = len(section) // 2
        plan_calls(model=2)
        for part in (section[:half], section[half:]):
            user = self._user(run, part)
            reply = self._first_reply(run, part, user)
            self._accept(run, part, user, reply, depth=depth + 1)

    def _call(
        self, run: _Run, section: Sequence[NumberedLine], user: str
    ) -> DocumentChunkResponse:
        caps = self._structured.capabilities
        available = caps.context_window_tokens - section_input_tokens(section)
        # Repairs contain the previous response too, so include their extra text.
        available -= max(0, (len(user) - len(self._user(run, section)) + 3) // 4)
        if available <= 0:
            raise ProviderInputTooLargeError("chunking input exceeds model context")
        result = None
        try:
            result = self._structured.complete_structured(
                StructuredRequest(
                    contract=_CONTRACTS[run.request.kind],
                    system=document_system(run.request.kind),
                    user=user,
                    max_output_tokens=min(self._output_limit(), available),
                    temperature=0.0 if caps.supports_temperature else None,
                    seed=0 if caps.supports_seed else None,
                )
            )
            return result.value
        except StructuredOutputInvalidError as error:
            raise ChunkingIncompleteError("chunking_invalid_output") from error
        finally:
            self._record(run, result)

    def _output_limit(self) -> int:
        caps = self._structured.capabilities
        limit = caps.execution.document_output_limit(caps.max_output_tokens)
        return min(limit, self._max_output_tokens or limit)

    def _record(
        self, run: _Run, result: StructuredResult[DocumentChunkResponse] | None
    ) -> None:
        with self._lock:
            run.calls += 1
            if result is not None:
                run.provider_id = result.provider_id
                run.model_tag = result.model_tag
                run.left_machine = run.left_machine or result.left_machine

    def _inferred_edges(self, run: _Run) -> tuple[GraphEdge, ...]:
        terms = [
            term.canonical
            for chunk in run.chunks
            for term in (
                *chunk.tech_terms,
                *(
                    term
                    for requirement in chunk.atomic_requirements
                    for term in requirement.tech_terms
                ),
            )
        ]
        return edges_from_relations(terms, run.taxonomy)

    def _validate(
        self, run: _Run, section: Sequence[NumberedLine], reply: DocumentChunkResponse
    ) -> ChunkPlan:
        return validate_chunk_plan(
            run.request.kind,
            section,
            run.request.text,
            proposals_from_chunks(reply.chunks),
            limits=self._limits,
            advert_title=run.request.advert_title,
            known_role_headings=run.headings,
        )
