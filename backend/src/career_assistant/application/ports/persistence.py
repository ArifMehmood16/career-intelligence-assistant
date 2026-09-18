"""Persistence ports — application depends on these, never on SQLAlchemy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from career_assistant.domain.claims import Claim
from career_assistant.domain.documents import DocumentKind, Span
from career_assistant.domain.groundedness import GroundednessVerdict
from career_assistant.domain.jobs import AnalysisJob, RoleStatus
from career_assistant.domain.mapping import RequirementMapping
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoreExplanation


class ParseStatus(StrEnum):
    PARSED = "parsed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class StoredDocument:
    id: str
    workspace_id: str
    kind: DocumentKind
    filename: str
    media_type: str
    byte_length: int
    sha256: str
    original_bytes: bytes
    normalised_text: str
    parse_status: ParseStatus
    page_count: int
    character_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class NewDocument:
    id: str
    kind: DocumentKind
    filename: str
    media_type: str
    original_bytes: bytes
    sha256: str
    normalised_text: str
    parse_status: ParseStatus
    page_count: int
    character_count: int
    is_active: bool
    spans: tuple[Span, ...]


@dataclass(frozen=True, slots=True)
class RoleRecord:
    id: str
    workspace_id: str
    title: str
    job_description_document_id: str
    analysis_version: int
    status: RoleStatus
    created_at: datetime


@dataclass(frozen=True, slots=True)
class QuestionRecord:
    id: str
    workspace_id: str
    conversation_id: str
    client_request_id: str
    text: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AnswerRecord:
    id: str
    workspace_id: str
    question_id: str
    body: str
    provider: str
    model_tag: str
    left_machine: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class HistoryMessage:
    id: str
    kind: str  # question | answer
    content: str
    created_at: datetime
    provider: str | None = None
    model_tag: str | None = None
    left_machine: bool | None = None


class WorkspaceRepository(Protocol):
    def ensure(self, workspace_id: str) -> None: ...


class DocumentRepository(Protocol):
    def save_admitted(
        self, workspace_id: str, document: NewDocument
    ) -> StoredDocument: ...

    def get(self, workspace_id: str, document_id: str) -> StoredDocument | None: ...

    def get_active_cv(self, workspace_id: str) -> StoredDocument | None: ...

    def list_spans(self, workspace_id: str, document_id: str) -> tuple[Span, ...]: ...

    def hard_delete(self, workspace_id: str, document_id: str) -> None: ...

    def replace_cv(
        self, workspace_id: str, new_document: NewDocument
    ) -> StoredDocument: ...


class ConversationRepository(Protocol):
    def create_conversation(self, workspace_id: str, conversation_id: str) -> None: ...

    def add_question(
        self,
        workspace_id: str,
        *,
        conversation_id: str,
        question_id: str,
        client_request_id: str,
        text: str,
    ) -> QuestionRecord: ...

    def add_answer(
        self,
        workspace_id: str,
        *,
        question_id: str,
        answer_id: str,
        body: str,
        provider: str,
        model_tag: str,
        left_machine: bool,
        citation_span_ids: tuple[str, ...],
    ) -> AnswerRecord: ...

    def get_by_client_request_id(
        self, workspace_id: str, client_request_id: str
    ) -> tuple[QuestionRecord, AnswerRecord] | None: ...

    def list_answer_citations(
        self, workspace_id: str, answer_id: str
    ) -> tuple[str, ...]: ...

    def list_history(
        self, workspace_id: str, conversation_id: str
    ) -> tuple[HistoryMessage, ...]: ...

    def hard_delete_history(self, workspace_id: str, conversation_id: str) -> None: ...


class RoleRepository(Protocol):
    def create(
        self,
        *,
        workspace_id: str,
        role_id: str,
        title: str,
        job_description_document_id: str,
        status: RoleStatus,
    ) -> RoleRecord: ...

    def get(self, workspace_id: str, role_id: str) -> RoleRecord | None: ...

    def list_for_workspace(self, workspace_id: str) -> tuple[RoleRecord, ...]: ...

    def set_status(
        self, workspace_id: str, role_id: str, status: RoleStatus
    ) -> RoleRecord: ...


class AnalysisJobRepository(Protocol):
    def enqueue(self, job: AnalysisJob) -> AnalysisJob: ...

    def enqueue_idempotent(self, job: AnalysisJob) -> AnalysisJob: ...

    def get(self, workspace_id: str, job_id: str) -> AnalysisJob | None: ...

    def save(self, job: AnalysisJob) -> AnalysisJob: ...

    def enqueue_reanalysis_for_workspace(
        self,
        *,
        workspace_id: str,
        job_ids: tuple[str, ...],
        created_at: datetime,
    ) -> tuple[str, ...]: ...


class AnalysisResultRepository(Protocol):
    def publish(
        self,
        *,
        workspace_id: str,
        role_id: str,
        analysis_version: int,
        cv_document_id: str,
        requirements: tuple[Requirement, ...],
        claims: tuple[Claim, ...],
        mappings: tuple[RequirementMapping, ...],
        explanation: ScoreExplanation,
        job: AnalysisJob,
    ) -> None: ...

    def fail_job(
        self,
        *,
        workspace_id: str,
        role_id: str,
        job: AnalysisJob,
    ) -> None: ...

    def list_mappings(
        self, workspace_id: str, role_id: str
    ) -> tuple[RequirementMapping, ...]: ...


@dataclass(frozen=True, slots=True)
class NewGeneratedDraft:
    id: str
    workspace_id: str
    role_id: str
    kind: str
    body: str
    analysis_version: int
    citation_span_ids: tuple[str, ...]
    provider: str
    model_tag: str
    left_machine: bool
    groundedness: GroundednessVerdict
    used_template_fallback: bool
    regeneration_count: int


@dataclass(frozen=True, slots=True)
class GeneratedDraftRecord:
    id: str
    workspace_id: str
    role_id: str
    kind: str
    body: str
    analysis_version: int
    version: int
    citation_span_ids: tuple[str, ...]
    provider: str
    model_tag: str
    left_machine: bool
    groundedness: GroundednessVerdict
    used_template_fallback: bool
    regeneration_count: int
    created_at: datetime


class DraftRepository(Protocol):
    def save(self, draft: NewGeneratedDraft) -> GeneratedDraftRecord: ...

    def get(self, workspace_id: str, draft_id: str) -> GeneratedDraftRecord | None: ...

    def list_for_role(
        self, workspace_id: str, role_id: str, *, kind: str | None = None
    ) -> tuple[GeneratedDraftRecord, ...]: ...

    def get_latest(
        self, workspace_id: str, role_id: str, *, kind: str
    ) -> GeneratedDraftRecord | None: ...


class UnitOfWork(Protocol):
    workspaces: WorkspaceRepository
    documents: DocumentRepository
    conversations: ConversationRepository
    roles: RoleRepository
    jobs: AnalysisJobRepository
    analysis: AnalysisResultRepository
    drafts: DraftRepository

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(self, *exc: object) -> None: ...
