"""Hermetic in-memory conversation store for AskService."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class MemoryMessage:
    id: str
    author: str
    content: str
    kind: str
    citations: tuple[str, ...]
    provider: str | None
    model: str | None
    left_machine: bool
    client_request_id: str | None
    created_at: datetime
    conversation_id: str
    workspace_id: str


@dataclass
class InMemoryConversationStore:
    """Process-local conversation history — API hermetic default only."""

    messages: list[MemoryMessage] = field(default_factory=list)
    conversations: dict[str, str] = field(default_factory=dict)

    def ensure_conversation(self, workspace_id: str) -> str:
        existing = self.conversations.get(workspace_id)
        if existing is not None:
            return existing
        conversation_id = str(uuid.uuid4())
        self.conversations[workspace_id] = conversation_id
        return conversation_id

    def conversation_id_for(self, workspace_id: str) -> str | None:
        return self.conversations.get(workspace_id)

    def find_by_client_request_id(
        self, workspace_id: str, client_request_id: str
    ) -> tuple[MemoryMessage, MemoryMessage] | None:
        question = next(
            (
                message
                for message in self.messages
                if message.workspace_id == workspace_id
                and message.author == "user"
                and message.client_request_id == client_request_id
            ),
            None,
        )
        if question is None:
            return None
        answer = next(
            (
                message
                for message in self.messages
                if message.workspace_id == workspace_id
                and message.author == "assistant"
                and message.client_request_id == client_request_id
            ),
            None,
        )
        if answer is None:
            return None
        return question, answer

    def persist_question(
        self,
        *,
        workspace_id: str,
        conversation_id: str,
        question_id: str,
        client_request_id: str,
        text: str,
    ) -> None:
        self.messages.append(
            MemoryMessage(
                id=question_id,
                author="user",
                content=text,
                kind="question",
                citations=(),
                provider=None,
                model=None,
                left_machine=False,
                client_request_id=client_request_id,
                created_at=datetime.now(UTC),
                conversation_id=conversation_id,
                workspace_id=workspace_id,
            )
        )

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
        question = next(
            (
                message
                for message in self.messages
                if message.id == question_id and message.workspace_id == workspace_id
            ),
            None,
        )
        conversation_id = (
            question.conversation_id if question is not None else str(uuid.uuid4())
        )
        client_request_id = question.client_request_id if question is not None else None
        self.messages.append(
            MemoryMessage(
                id=answer_id,
                author="assistant",
                content=body,
                kind=kind,
                citations=citations,
                provider=provider,
                model=model_tag,
                left_machine=left_machine,
                client_request_id=client_request_id,
                created_at=datetime.now(UTC),
                conversation_id=conversation_id,
                workspace_id=workspace_id,
            )
        )

    def list_history(
        self, workspace_id: str, conversation_id: str
    ) -> tuple[MemoryMessage, ...]:
        return tuple(
            message
            for message in self.messages
            if message.workspace_id == workspace_id
            and message.conversation_id == conversation_id
        )

    def hard_delete(self, workspace_id: str, conversation_id: str) -> None:
        self.messages = [
            message
            for message in self.messages
            if not (
                message.workspace_id == workspace_id
                and message.conversation_id == conversation_id
            )
        ]
        if self.conversations.get(workspace_id) == conversation_id:
            del self.conversations[workspace_id]
