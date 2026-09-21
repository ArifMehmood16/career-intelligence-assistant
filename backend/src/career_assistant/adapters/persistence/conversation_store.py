"""SQL-backed ConversationStore for the production Ask HTTP path."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC

from sqlalchemy.exc import IntegrityError

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ask.memory import MemoryMessage
from career_assistant.application.ports.persistence import (
    AnswerRecord,
    HistoryMessage,
    QuestionRecord,
)


class SqlConversationStore:
    """Ask ConversationStore over SqlUnitOfWork. One conversation per workspace."""

    def __init__(self, uow_factory: Callable[[], SqlUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def conversation_id_for(self, workspace_id: str) -> str | None:
        with self._uow_factory() as uow:
            return uow.conversations.conversation_id_for(workspace_id)

    def ensure_conversation(self, workspace_id: str) -> str:
        with self._uow_factory() as uow:
            uow.workspaces.ensure(workspace_id)
            existing = uow.conversations.conversation_id_for(workspace_id)
            if existing is not None:
                return existing
            conversation_id = str(uuid.uuid4())
            uow.conversations.create_conversation(workspace_id, conversation_id)
            uow.commit()
            return conversation_id

    def find_by_client_request_id(
        self, workspace_id: str, client_request_id: str
    ) -> tuple[MemoryMessage, MemoryMessage] | None:
        with self._uow_factory() as uow:
            found = uow.conversations.get_by_client_request_id(
                workspace_id, client_request_id
            )
            if found is None:
                return None
            question, answer = found
            citations = uow.conversations.list_answer_citations(workspace_id, answer.id)
            return (
                _question_message(question, client_request_id),
                _answer_message(answer, question.conversation_id, citations),
            )

    def persist_question(
        self,
        *,
        workspace_id: str,
        conversation_id: str,
        question_id: str,
        client_request_id: str,
        text: str,
    ) -> None:
        with self._uow_factory() as uow:
            uow.workspaces.ensure(workspace_id)
            if (
                uow.conversations.get_by_client_request_id(
                    workspace_id, client_request_id
                )
                is not None
            ):
                return
            try:
                uow.conversations.add_question(
                    workspace_id,
                    conversation_id=conversation_id,
                    question_id=question_id,
                    client_request_id=client_request_id,
                    text=text,
                )
                uow.commit()
            except IntegrityError:
                uow.rollback()

    def persist_answer(
        self,
        *,
        workspace_id: str,
        question_id: str,
        answer_id: str,
        body: str,
        kind: str,
        citations: tuple[str, ...],
        provider: str,
        model_tag: str,
        left_machine: bool,
    ) -> None:
        with self._uow_factory() as uow:
            try:
                uow.conversations.add_answer(
                    workspace_id,
                    question_id=question_id,
                    answer_id=answer_id,
                    body=body,
                    kind=kind,
                    provider=provider,
                    model_tag=model_tag,
                    left_machine=left_machine,
                    citation_span_ids=citations,
                )
                uow.commit()
            except IntegrityError:
                uow.rollback()

    def list_history(
        self, workspace_id: str, conversation_id: str
    ) -> tuple[MemoryMessage, ...]:
        with self._uow_factory() as uow:
            records = uow.conversations.list_history(workspace_id, conversation_id)
            messages: list[MemoryMessage] = []
            for record in records:
                if record.kind == "question":
                    messages.append(
                        _history_question(record, workspace_id, conversation_id)
                    )
                    continue
                citations = uow.conversations.list_answer_citations(
                    workspace_id, record.id
                )
                messages.append(
                    _history_answer(record, workspace_id, conversation_id, citations)
                )
            return tuple(messages)

    def hard_delete(self, workspace_id: str, conversation_id: str) -> None:
        with self._uow_factory() as uow:
            uow.conversations.hard_delete_history(workspace_id, conversation_id)
            uow.commit()


def _question_message(
    question: QuestionRecord, client_request_id: str
) -> MemoryMessage:
    created = question.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return MemoryMessage(
        id=question.id,
        author="user",
        content=question.text,
        kind="question",
        citations=(),
        provider=None,
        model=None,
        left_machine=False,
        client_request_id=client_request_id,
        created_at=created,
        conversation_id=question.conversation_id,
        workspace_id=question.workspace_id,
    )


def _answer_message(
    answer: AnswerRecord, conversation_id: str, citations: tuple[str, ...]
) -> MemoryMessage:
    created = answer.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return MemoryMessage(
        id=answer.id,
        author="assistant",
        content=answer.body,
        kind=answer.kind,
        citations=citations,
        provider=answer.provider,
        model=answer.model_tag,
        left_machine=answer.left_machine,
        client_request_id=None,
        created_at=created,
        conversation_id=conversation_id,
        workspace_id=answer.workspace_id,
    )


def _history_question(
    record: HistoryMessage, workspace_id: str, conversation_id: str
) -> MemoryMessage:
    created = record.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return MemoryMessage(
        id=record.id,
        author="user",
        content=record.content,
        kind="question",
        citations=(),
        provider=None,
        model=None,
        left_machine=False,
        client_request_id=None,
        created_at=created,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
    )


def _history_answer(
    record: HistoryMessage,
    workspace_id: str,
    conversation_id: str,
    citations: tuple[str, ...],
) -> MemoryMessage:
    created = record.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return MemoryMessage(
        id=record.id,
        author="assistant",
        content=record.content,
        kind=record.kind,
        citations=citations,
        provider=record.provider,
        model=record.model_tag,
        left_machine=bool(record.left_machine),
        client_request_id=None,
        created_at=created,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
    )
