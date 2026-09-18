"""SQLAlchemy unit of work and repository adapters."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.analysis_repos import (
    SqlAnalysisJobRepository,
    SqlAnalysisResultRepository,
    SqlRoleRepository,
)
from career_assistant.adapters.persistence.draft_repos import SqlDraftRepository
from career_assistant.adapters.persistence.models import (
    AnswerCitationRow,
    AnswerRow,
    ConversationRow,
    DocumentRow,
    GeneratedDraftRow,
    MappingRow,
    QuestionRow,
    ScoreExplanationRow,
    SpanRow,
    WorkspaceRow,
)
from career_assistant.application.ports.persistence import (
    AnalysisJobRepository,
    AnalysisResultRepository,
    AnswerRecord,
    ConversationRepository,
    DocumentRepository,
    DraftRepository,
    HistoryMessage,
    NewDocument,
    ParseStatus,
    QuestionRecord,
    RoleRepository,
    StoredDocument,
    WorkspaceRepository,
)
from career_assistant.domain.documents import DocumentKind, Span


def _as_uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def _to_stored(row: DocumentRow) -> StoredDocument:
    return StoredDocument(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        kind=DocumentKind(row.kind),
        filename=row.filename,
        media_type=row.media_type,
        byte_length=row.byte_length,
        sha256=row.sha256,
        original_bytes=bytes(row.original_bytes),
        normalised_text=row.normalised_text,
        parse_status=ParseStatus(row.parse_status),
        page_count=row.page_count,
        character_count=row.character_count,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlWorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure(self, workspace_id: str) -> None:
        wid = _as_uuid(workspace_id)
        existing = self._session.get(WorkspaceRow, wid)
        if existing is None:
            self._session.add(WorkspaceRow(id=wid))
            self._session.flush()


class SqlDocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_admitted(self, workspace_id: str, document: NewDocument) -> StoredDocument:
        wid = _as_uuid(workspace_id)
        doc_id = _as_uuid(document.id)
        row = DocumentRow(
            id=doc_id,
            workspace_id=wid,
            kind=document.kind.value,
            filename=document.filename,
            media_type=document.media_type,
            byte_length=len(document.original_bytes),
            sha256=document.sha256,
            original_bytes=document.original_bytes,
            normalised_text=document.normalised_text,
            parse_status=document.parse_status.value,
            page_count=document.page_count,
            character_count=document.character_count,
            is_active=document.is_active,
        )
        self._session.add(row)
        for span in document.spans:
            self._session.add(
                SpanRow(
                    id=_as_uuid(span.id),
                    workspace_id=wid,
                    document_id=doc_id,
                    page_number=span.page_number,
                    start_offset=span.start_offset,
                    end_offset=span.end_offset,
                    text=span.text,
                )
            )
        self._session.flush()
        return _to_stored(row)

    def get(self, workspace_id: str, document_id: str) -> StoredDocument | None:
        row = self._session.scalar(
            select(DocumentRow).where(
                DocumentRow.workspace_id == _as_uuid(workspace_id),
                DocumentRow.id == _as_uuid(document_id),
            )
        )
        return _to_stored(row) if row is not None else None

    def get_active_cv(self, workspace_id: str) -> StoredDocument | None:
        row = self._session.scalar(
            select(DocumentRow).where(
                DocumentRow.workspace_id == _as_uuid(workspace_id),
                DocumentRow.kind == DocumentKind.CV.value,
                DocumentRow.is_active.is_(True),
            )
        )
        return _to_stored(row) if row is not None else None

    def list_spans(self, workspace_id: str, document_id: str) -> tuple[Span, ...]:
        rows = self._session.scalars(
            select(SpanRow)
            .where(
                SpanRow.workspace_id == _as_uuid(workspace_id),
                SpanRow.document_id == _as_uuid(document_id),
            )
            .order_by(SpanRow.page_number, SpanRow.start_offset)
        ).all()
        return tuple(
            Span(
                id=str(row.id),
                document_id=str(row.document_id),
                page_number=row.page_number,
                start_offset=row.start_offset,
                end_offset=row.end_offset,
                text=row.text,
            )
            for row in rows
        )

    def ensure_spans(
        self, workspace_id: str, document_id: str, spans: tuple[Span, ...]
    ) -> None:
        wid = _as_uuid(workspace_id)
        doc_id = _as_uuid(document_id)
        for span in spans:
            existing = self._session.get(SpanRow, _as_uuid(span.id))
            if existing is not None:
                continue
            self._session.add(
                SpanRow(
                    id=_as_uuid(span.id),
                    workspace_id=wid,
                    document_id=doc_id,
                    page_number=span.page_number,
                    start_offset=span.start_offset,
                    end_offset=span.end_offset,
                    text=span.text,
                )
            )
        self._session.flush()

    def hard_delete(self, workspace_id: str, document_id: str) -> None:
        row = self._session.scalar(
            select(DocumentRow).where(
                DocumentRow.workspace_id == _as_uuid(workspace_id),
                DocumentRow.id == _as_uuid(document_id),
            )
        )
        if row is None:
            return
        self._session.delete(row)
        self._session.flush()

    def replace_cv(
        self, workspace_id: str, new_document: NewDocument
    ) -> StoredDocument:
        wid = _as_uuid(workspace_id)
        # Invalidate mappings/scores/drafts that depended on the previous CV.
        for mapping in self._session.scalars(
            select(MappingRow).where(MappingRow.workspace_id == wid)
        ).all():
            mapping.invalidated = True
        for score in self._session.scalars(
            select(ScoreExplanationRow).where(ScoreExplanationRow.workspace_id == wid)
        ).all():
            score.invalidated = True
        for draft in self._session.scalars(
            select(GeneratedDraftRow).where(GeneratedDraftRow.workspace_id == wid)
        ).all():
            draft.invalidated = True

        previous = self.get_active_cv(workspace_id)
        if previous is not None:
            prev_row = self._session.get(DocumentRow, _as_uuid(previous.id))
            if prev_row is not None:
                prev_row.is_active = False
                self._session.flush()

        stored = self.save_admitted(workspace_id, new_document)
        if previous is not None:
            self.hard_delete(workspace_id, previous.id)
        self._session.flush()
        return stored

    def list_cover_letters(self, workspace_id: str) -> tuple[StoredDocument, ...]:
        rows = self._session.scalars(
            select(DocumentRow)
            .where(
                DocumentRow.workspace_id == _as_uuid(workspace_id),
                DocumentRow.kind == DocumentKind.COVER_LETTER.value,
            )
            .order_by(DocumentRow.created_at.asc())
        ).all()
        return tuple(_to_stored(row) for row in rows)


class SqlConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_conversation(self, workspace_id: str, conversation_id: str) -> None:
        self._session.add(
            ConversationRow(
                id=_as_uuid(conversation_id),
                workspace_id=_as_uuid(workspace_id),
            )
        )
        self._session.flush()

    def add_question(
        self,
        workspace_id: str,
        *,
        conversation_id: str,
        question_id: str,
        client_request_id: str,
        text: str,
    ) -> QuestionRecord:
        row = QuestionRow(
            id=_as_uuid(question_id),
            workspace_id=_as_uuid(workspace_id),
            conversation_id=_as_uuid(conversation_id),
            client_request_id=client_request_id,
            text=text,
        )
        self._session.add(row)
        self._session.flush()
        return QuestionRecord(
            id=str(row.id),
            workspace_id=str(row.workspace_id),
            conversation_id=str(row.conversation_id),
            client_request_id=row.client_request_id,
            text=row.text,
            created_at=row.created_at or datetime.now(UTC),
        )

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
    ) -> AnswerRecord:
        wid = _as_uuid(workspace_id)
        row = AnswerRow(
            id=_as_uuid(answer_id),
            workspace_id=wid,
            question_id=_as_uuid(question_id),
            body=body,
            provider=provider,
            model_tag=model_tag,
            left_machine=left_machine,
        )
        self._session.add(row)
        self._session.flush()
        for span_id in citation_span_ids:
            self._session.add(
                AnswerCitationRow(
                    workspace_id=wid,
                    answer_id=row.id,
                    span_id=_as_uuid(span_id),
                )
            )
        self._session.flush()
        return AnswerRecord(
            id=str(row.id),
            workspace_id=str(row.workspace_id),
            question_id=str(row.question_id),
            body=row.body,
            provider=row.provider,
            model_tag=row.model_tag,
            left_machine=row.left_machine,
            created_at=row.created_at or datetime.now(UTC),
        )

    def get_by_client_request_id(
        self, workspace_id: str, client_request_id: str
    ) -> tuple[QuestionRecord, AnswerRecord] | None:
        question = self._session.scalar(
            select(QuestionRow).where(
                QuestionRow.workspace_id == _as_uuid(workspace_id),
                QuestionRow.client_request_id == client_request_id,
            )
        )
        if question is None:
            return None
        answer = self._session.scalar(
            select(AnswerRow).where(
                AnswerRow.workspace_id == _as_uuid(workspace_id),
                AnswerRow.question_id == question.id,
            )
        )
        if answer is None:
            return None
        return (
            QuestionRecord(
                id=str(question.id),
                workspace_id=str(question.workspace_id),
                conversation_id=str(question.conversation_id),
                client_request_id=question.client_request_id,
                text=question.text,
                created_at=question.created_at or datetime.now(UTC),
            ),
            AnswerRecord(
                id=str(answer.id),
                workspace_id=str(answer.workspace_id),
                question_id=str(answer.question_id),
                body=answer.body,
                provider=answer.provider,
                model_tag=answer.model_tag,
                left_machine=answer.left_machine,
                created_at=answer.created_at or datetime.now(UTC),
            ),
        )

    def list_answer_citations(
        self, workspace_id: str, answer_id: str
    ) -> tuple[str, ...]:
        rows = self._session.scalars(
            select(AnswerCitationRow).where(
                AnswerCitationRow.workspace_id == _as_uuid(workspace_id),
                AnswerCitationRow.answer_id == _as_uuid(answer_id),
            )
        ).all()
        return tuple(str(row.span_id) for row in rows)

    def list_history(
        self, workspace_id: str, conversation_id: str
    ) -> tuple[HistoryMessage, ...]:
        questions = self._session.scalars(
            select(QuestionRow)
            .where(
                QuestionRow.workspace_id == _as_uuid(workspace_id),
                QuestionRow.conversation_id == _as_uuid(conversation_id),
            )
            .order_by(QuestionRow.created_at.asc(), QuestionRow.id.asc())
        ).all()
        messages: list[HistoryMessage] = []
        for question in questions:
            messages.append(
                HistoryMessage(
                    id=str(question.id),
                    kind="question",
                    content=question.text,
                    created_at=question.created_at or datetime.now(UTC),
                )
            )
            answer = self._session.scalar(
                select(AnswerRow).where(AnswerRow.question_id == question.id)
            )
            if answer is not None:
                messages.append(
                    HistoryMessage(
                        id=str(answer.id),
                        kind="answer",
                        content=answer.body,
                        created_at=answer.created_at or datetime.now(UTC),
                        provider=answer.provider,
                        model_tag=answer.model_tag,
                        left_machine=answer.left_machine,
                    )
                )
        return tuple(messages)

    def hard_delete_history(self, workspace_id: str, conversation_id: str) -> None:
        row = self._session.scalar(
            select(ConversationRow).where(
                ConversationRow.workspace_id == _as_uuid(workspace_id),
                ConversationRow.id == _as_uuid(conversation_id),
            )
        )
        if row is None:
            return
        self._session.delete(row)
        self._session.flush()


class SqlUnitOfWork:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._session_factory = factory
        self._session: Session | None = None
        self.workspaces: WorkspaceRepository
        self.documents: DocumentRepository
        self.conversations: ConversationRepository
        self.roles: RoleRepository
        self.jobs: AnalysisJobRepository
        self.analysis: AnalysisResultRepository
        self.drafts: DraftRepository

    def __enter__(self) -> SqlUnitOfWork:
        self._session = self._session_factory()
        self.workspaces = SqlWorkspaceRepository(self._session)
        self.documents = SqlDocumentRepository(self._session)
        self.conversations = SqlConversationRepository(self._session)
        self.roles = SqlRoleRepository(self._session)
        self.jobs = SqlAnalysisJobRepository(self._session, self.roles)
        self.analysis = SqlAnalysisResultRepository(
            self._session, self.roles, self.jobs
        )
        self.drafts = SqlDraftRepository(self._session)
        return self

    def __exit__(self, *exc: object) -> None:
        assert self._session is not None
        if exc[0] is not None:
            self._session.rollback()
        self._session.close()
        self._session = None

    def commit(self) -> None:
        assert self._session is not None
        self._session.commit()

    def rollback(self) -> None:
        assert self._session is not None
        self._session.rollback()
