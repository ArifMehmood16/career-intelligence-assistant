"""Chunk a stored document with a model, verified by the server (PLAN 18.4).

One structured call per section; a plan that breaks a structural rule goes back to
the model once with the problems listed; a reply cut by the output limit splits its
section in half. Anything else that fails is an incomplete ingestion: no chunks are
kept and the error carries codes and counts, never document text.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from career_assistant.application.chunking.mapping import proposals_from
from career_assistant.application.chunking.prompts import (
    CHUNKING_PROMPT_VERSION,
    chunking_system,
    chunking_user,
    repair_user,
)
from career_assistant.application.chunking.sections import (
    ChunkingBudget,
    plan_sections,
)
from career_assistant.application.contracts.chunking import (
    CoverLetterChunkingResponse,
    CvChunkingResponse,
    JobChunkingResponse,
)
from career_assistant.application.ports.errors import (
    StructuredOutputInvalidError,
    StructuredOutputTruncatedError,
)
from career_assistant.application.ports.structured import (
    StructuredCompletionPort,
    StructuredRequest,
)
from career_assistant.domain.chunking import (
    DEFAULT_CHUNK_LIMITS,
    Chunk,
    ChunkLimits,
    ChunkPlan,
    validate_chunk_plan,
)
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.lines import NumberedLine, number_lines

ChunkingResponse = (
    CvChunkingResponse | CoverLetterChunkingResponse | JobChunkingResponse
)

_CONTRACTS: dict[DocumentKind, type[ChunkingResponse]] = {
    DocumentKind.CV: CvChunkingResponse,
    DocumentKind.COVER_LETTER: CoverLetterChunkingResponse,
    DocumentKind.JOB_DESCRIPTION: JobChunkingResponse,
}
DEFAULT_MAX_OUTPUT_TOKENS = 8_000


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


@dataclass
class _Run:
    request: ChunkingRequest
    total_lines: int
    chunks: list[Chunk] = field(default_factory=list)
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
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    ) -> None:
        self._structured = structured
        self._limits = limits
        self._max_output_tokens = max_output_tokens

    def chunk(self, request: ChunkingRequest) -> ChunkingOutcome:
        lines = number_lines(request.text)
        if not lines:
            raise ChunkingIncompleteError("empty_document")
        run = _Run(request=request, total_lines=len(lines))
        for section in plan_sections(lines, self._budget()):
            self._chunk_section(run, section)
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
        )

    def _budget(self) -> ChunkingBudget:
        caps = self._structured.capabilities
        output = self._output_tokens()
        return ChunkingBudget(
            max_input_tokens=caps.context_window_tokens - output,
            max_output_tokens=output,
        )

    def _output_tokens(self) -> int:
        model_limit = self._structured.capabilities.max_output_tokens
        return min(model_limit, self._max_output_tokens)

    def _chunk_section(self, run: _Run, section: Sequence[NumberedLine]) -> None:
        try:
            plan = self._plan(run, section)
        except StructuredOutputTruncatedError as error:
            if len(section) < 2:
                raise ChunkingIncompleteError("chunking_truncated") from error
            half = len(section) // 2
            self._chunk_section(run, section[:half])
            self._chunk_section(run, section[half:])
            return
        run.accept(plan)

    def _plan(self, run: _Run, section: Sequence[NumberedLine]) -> ChunkPlan:
        user = chunking_user(
            run.request.kind,
            section,
            total_lines=run.total_lines,
            advert_title=run.request.advert_title,
        )
        reply = self._call(run, user)
        plan = self._validate(run, section, reply)
        if not plan.problems:
            return plan
        run.repairs += 1
        previous = reply.model_dump_json(exclude_none=True)
        reply = self._call(run, repair_user(user, previous, plan.problems))
        plan = self._validate(run, section, reply)
        if plan.problems:
            raise ChunkingIncompleteError(
                "chunking_incomplete", problem_count=len(plan.problems)
            )
        return plan

    def _call(self, run: _Run, user: str) -> ChunkingResponse:
        contract = _CONTRACTS[run.request.kind]
        try:
            result = self._structured.complete_structured(
                StructuredRequest(
                    contract=contract,
                    system=chunking_system(run.request.kind),
                    user=user,
                    max_output_tokens=self._output_tokens(),
                    temperature=0.0,
                    seed=0,
                )
            )
        except StructuredOutputInvalidError as error:
            raise ChunkingIncompleteError("chunking_invalid_output") from error
        finally:
            run.calls += 1
        run.provider_id = result.provider_id
        run.model_tag = result.model_tag
        run.left_machine = run.left_machine or result.left_machine
        return result.value

    def _validate(
        self, run: _Run, section: Sequence[NumberedLine], reply: ChunkingResponse
    ) -> ChunkPlan:
        return validate_chunk_plan(
            run.request.kind,
            section,
            run.request.text,
            proposals_from(reply.chunks),
            limits=self._limits,
            advert_title=run.request.advert_title,
            known_role_headings=run.headings,
        )
