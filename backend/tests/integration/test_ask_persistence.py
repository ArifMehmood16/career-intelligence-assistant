"""Phase 9.8–9.9 — conversation idempotency and ordered history (Postgres)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from tests.integration.conftest import make_document

from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.domain.documents import DocumentKind

pytestmark = pytest.mark.integration


def test_get_by_client_request_id_returns_question_and_answer(
    uow: SqlUnitOfWork,
) -> None:
    workspace_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    question_id = str(uuid.uuid4())
    answer_id = str(uuid.uuid4())
    span_doc = make_document(kind=DocumentKind.CV, text="Owned dbt models.")

    with uow:
        uow.workspaces.ensure(workspace_id)
        stored = uow.documents.save_admitted(workspace_id, span_doc)
        spans = uow.documents.list_spans(workspace_id, stored.id)
        uow.conversations.create_conversation(workspace_id, conversation_id)
        uow.conversations.add_question(
            workspace_id,
            conversation_id=conversation_id,
            question_id=question_id,
            client_request_id="cr-idempotent",
            text="What gaps should I close first?",
        )
        uow.conversations.add_answer(
            workspace_id,
            question_id=question_id,
            answer_id=answer_id,
            body="Close the CUDA gap first.",
            provider="mapping",
            model_tag="deterministic",
            left_machine=False,
            citation_span_ids=(spans[0].id,),
        )
        uow.commit()

    with uow:
        found = uow.conversations.get_by_client_request_id(
            workspace_id, "cr-idempotent"
        )
        assert found is not None
        question, answer = found
        assert question.text == "What gaps should I close first?"
        assert answer.body == "Close the CUDA gap first."
        assert answer.provider == "mapping"
        citations = uow.conversations.list_answer_citations(workspace_id, answer.id)
        assert citations == (spans[0].id,)


def test_list_history_is_deterministic_creation_order(uow: SqlUnitOfWork) -> None:
    workspace_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    q1, q2 = str(uuid.uuid4()), str(uuid.uuid4())
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())

    with uow:
        uow.workspaces.ensure(workspace_id)
        uow.conversations.create_conversation(workspace_id, conversation_id)
        uow.conversations.add_question(
            workspace_id,
            conversation_id=conversation_id,
            question_id=q1,
            client_request_id="cr-1",
            text="First?",
        )
        uow.conversations.add_answer(
            workspace_id,
            question_id=q1,
            answer_id=a1,
            body="First answer",
            provider="mapping",
            model_tag="deterministic",
            left_machine=False,
            citation_span_ids=(),
        )
        uow.conversations.add_question(
            workspace_id,
            conversation_id=conversation_id,
            question_id=q2,
            client_request_id="cr-2",
            text="Second?",
        )
        uow.conversations.add_answer(
            workspace_id,
            question_id=q2,
            answer_id=a2,
            body="Second answer",
            provider="mapping",
            model_tag="deterministic",
            left_machine=False,
            citation_span_ids=(),
        )
        uow.commit()

    with uow:
        history = uow.conversations.list_history(workspace_id, conversation_id)
        assert [item.kind for item in history] == [
            "question",
            "answer",
            "question",
            "answer",
        ]
        assert [item.content for item in history] == [
            "First?",
            "First answer",
            "Second?",
            "Second answer",
        ]


def test_hard_delete_removes_questions_answers_and_citations(
    uow: SqlUnitOfWork,
) -> None:
    workspace_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    question_id = str(uuid.uuid4())
    answer_id = str(uuid.uuid4())
    span_doc = make_document(kind=DocumentKind.CV, text="Owned dbt models.")

    with uow:
        uow.workspaces.ensure(workspace_id)
        stored = uow.documents.save_admitted(workspace_id, span_doc)
        spans = uow.documents.list_spans(workspace_id, stored.id)
        uow.conversations.create_conversation(workspace_id, conversation_id)
        uow.conversations.add_question(
            workspace_id,
            conversation_id=conversation_id,
            question_id=question_id,
            client_request_id="cr-del",
            text="Q",
        )
        uow.conversations.add_answer(
            workspace_id,
            question_id=question_id,
            answer_id=answer_id,
            body="A",
            provider="mapping",
            model_tag="deterministic",
            left_machine=False,
            citation_span_ids=(spans[0].id,),
        )
        uow.commit()

    with uow:
        uow.conversations.hard_delete_history(workspace_id, conversation_id)
        uow.commit()

    with uow:
        assert uow.conversations.list_history(workspace_id, conversation_id) == ()
        assert (
            uow.conversations.get_by_client_request_id(workspace_id, "cr-del") is None
        )


def test_duplicate_client_request_id_rejected_at_persistence(
    uow: SqlUnitOfWork,
) -> None:
    workspace_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    with uow:
        uow.workspaces.ensure(workspace_id)
        uow.conversations.create_conversation(workspace_id, conversation_id)
        uow.conversations.add_question(
            workspace_id,
            conversation_id=conversation_id,
            question_id=str(uuid.uuid4()),
            client_request_id="cr-unique",
            text="Once",
        )
        uow.commit()
    with uow:
        uow.workspaces.ensure(workspace_id)
        with pytest.raises(IntegrityError):
            uow.conversations.add_question(
                workspace_id,
                conversation_id=conversation_id,
                question_id=str(uuid.uuid4()),
                client_request_id="cr-unique",
                text="Twice",
            )
            uow.commit()
        uow.rollback()
