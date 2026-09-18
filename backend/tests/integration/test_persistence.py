"""Phase 4 persistence integration — requires PostgreSQL 16+ with pgvector."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.conftest import make_document

from career_assistant.adapters.persistence.migrate import downgrade_base, upgrade_head
from career_assistant.adapters.persistence.models import (
    RoleRow,
    ScoreExplanationRow,
)
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.domain.documents import DocumentKind
from career_assistant.settings import DatabaseSettings

pytestmark = pytest.mark.integration


def test_migrations_upgrade_and_downgrade(
    database_settings: DatabaseSettings,
) -> None:
    url = database_settings.test_database_url
    downgrade_base(url)
    upgrade_head(url)
    upgrade_head(url)  # idempotent head
    downgrade_base(url)
    upgrade_head(url)


def test_cv_and_cover_letter_round_trip_with_spans(uow: SqlUnitOfWork) -> None:
    workspace_id = str(uuid.uuid4())
    cv = make_document(kind=DocumentKind.CV, text="Built Airflow DAGs.")
    letter = make_document(
        kind=DocumentKind.COVER_LETTER,
        text="I am writing to apply.",
        is_active=False,
    )

    with uow:
        uow.workspaces.ensure(workspace_id)
        stored_cv = uow.documents.save_admitted(workspace_id, cv)
        stored_letter = uow.documents.save_admitted(workspace_id, letter)
        uow.commit()

    with uow:
        fetched = uow.documents.get(workspace_id, stored_cv.id)
        assert fetched is not None
        assert fetched.original_bytes == b"Built Airflow DAGs."
        assert fetched.kind is DocumentKind.CV
        spans = uow.documents.list_spans(workspace_id, stored_cv.id)
        assert len(spans) == 1
        assert spans[0].text == "Built Airflow DAGs."

        other = uow.documents.get(workspace_id, stored_letter.id)
        assert other is not None
        assert other.kind is DocumentKind.COVER_LETTER
        assert other.original_bytes == b"I am writing to apply."


def test_workspace_scoping_hides_foreign_documents(uow: SqlUnitOfWork) -> None:
    ws_a = str(uuid.uuid4())
    ws_b = str(uuid.uuid4())
    doc = make_document()

    with uow:
        uow.workspaces.ensure(ws_a)
        uow.workspaces.ensure(ws_b)
        stored = uow.documents.save_admitted(ws_a, doc)
        uow.commit()

    with uow:
        assert uow.documents.get(ws_b, stored.id) is None
        assert uow.documents.list_spans(ws_b, stored.id) == ()


def test_hard_delete_removes_document_bytes_and_spans(
    uow: SqlUnitOfWork, session_factory: sessionmaker[Session]
) -> None:
    workspace_id = str(uuid.uuid4())
    doc = make_document()

    with uow:
        uow.workspaces.ensure(workspace_id)
        stored = uow.documents.save_admitted(workspace_id, doc)
        uow.commit()

    with uow:
        uow.documents.hard_delete(workspace_id, stored.id)
        uow.commit()

    with uow:
        assert uow.documents.get(workspace_id, stored.id) is None
        assert uow.documents.list_spans(workspace_id, stored.id) == ()

    with session_factory() as session:
        remaining = session.execute(
            text("SELECT count(*) FROM documents WHERE id = CAST(:id AS uuid)"),
            {"id": stored.id},
        ).scalar_one()
        assert remaining == 0
        span_count = session.execute(
            text(
                "SELECT count(*) FROM spans WHERE document_id = CAST(:id AS uuid)"
            ),
            {"id": stored.id},
        ).scalar_one()
        assert span_count == 0


def test_cv_replacement_invalidates_scores_and_deletes_old(
    uow: SqlUnitOfWork, session_factory: sessionmaker[Session]
) -> None:
    workspace_id = str(uuid.uuid4())
    first = make_document(text="First CV")
    second = make_document(text="Second CV")
    jd = make_document(
        kind=DocumentKind.JOB_DESCRIPTION,
        text="Need Airflow.",
        is_active=False,
    )

    with uow:
        uow.workspaces.ensure(workspace_id)
        stored_first = uow.documents.save_admitted(workspace_id, first)
        stored_jd = uow.documents.save_admitted(workspace_id, jd)
        session = uow._session  # noqa: SLF001 — seed role/score for invalidation
        assert session is not None
        role_id = uuid.uuid4()
        session.add(
            RoleRow(
                id=role_id,
                workspace_id=uuid.UUID(workspace_id),
                title="Engineer",
                job_description_document_id=uuid.UUID(stored_jd.id),
                analysis_version=1,
            )
        )
        session.add(
            ScoreExplanationRow(
                id=uuid.uuid4(),
                workspace_id=uuid.UUID(workspace_id),
                role_id=role_id,
                analysis_version=1,
                score=80.0,
                band="strong",
                explanation={"summary": "seed"},
                invalidated=False,
            )
        )
        uow.commit()

    with uow:
        replaced = uow.documents.replace_cv(workspace_id, second)
        uow.commit()

    with uow:
        assert uow.documents.get(workspace_id, stored_first.id) is None
        active = uow.documents.get_active_cv(workspace_id)
        assert active is not None
        assert active.id == replaced.id
        assert active.original_bytes == b"Second CV"

    with session_factory() as session:
        score = session.scalars(select(ScoreExplanationRow)).one()
        assert score.invalidated is True


def test_conversation_client_request_id_and_one_answer_constraints(
    uow: SqlUnitOfWork,
) -> None:
    workspace_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    cv = make_document()

    with uow:
        uow.workspaces.ensure(workspace_id)
        uow.documents.save_admitted(workspace_id, cv)
        uow.conversations.create_conversation(workspace_id, conversation_id)
        q1 = uow.conversations.add_question(
            workspace_id,
            conversation_id=conversation_id,
            question_id=str(uuid.uuid4()),
            client_request_id="req-1",
            text="What evidence do I have for Airflow?",
        )
        uow.conversations.add_answer(
            workspace_id,
            question_id=q1.id,
            answer_id=str(uuid.uuid4()),
            body="You built Airflow DAGs.",
            provider="hermetic",
            model_tag="lexical-hash-v1",
            left_machine=False,
            citation_span_ids=(cv.spans[0].id,),
        )
        uow.commit()

    with uow:
        with pytest.raises(IntegrityError):
            uow.conversations.add_question(
                workspace_id,
                conversation_id=conversation_id,
                question_id=str(uuid.uuid4()),
                client_request_id="req-1",
                text="duplicate client id",
            )
        uow.rollback()

    with uow:
        q2 = uow.conversations.add_question(
            workspace_id,
            conversation_id=conversation_id,
            question_id=str(uuid.uuid4()),
            client_request_id="req-2",
            text="Another question",
        )
        uow.conversations.add_answer(
            workspace_id,
            question_id=q2.id,
            answer_id=str(uuid.uuid4()),
            body="first",
            provider="hermetic",
            model_tag="lexical-hash-v1",
            left_machine=False,
            citation_span_ids=(cv.spans[0].id,),
        )
        with pytest.raises(IntegrityError):
            uow.conversations.add_answer(
                workspace_id,
                question_id=q2.id,
                answer_id=str(uuid.uuid4()),
                body="second",
                provider="hermetic",
                model_tag="lexical-hash-v1",
                left_machine=False,
                citation_span_ids=(cv.spans[0].id,),
            )
        uow.rollback()


def test_failed_parse_rolls_back_without_readable_document(uow: SqlUnitOfWork) -> None:
    workspace_id = str(uuid.uuid4())
    with uow:
        uow.workspaces.ensure(workspace_id)
        uow.commit()

    with uow:
        uow.workspaces.ensure(workspace_id)
        try:
            raise RuntimeError("parse failed")
        except RuntimeError:
            uow.rollback()

    with uow:
        assert uow.documents.get_active_cv(workspace_id) is None


def test_chat_history_hard_delete_removes_questions_and_answers(
    uow: SqlUnitOfWork, session_factory: sessionmaker[Session]
) -> None:
    workspace_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    cv = make_document()

    with uow:
        uow.workspaces.ensure(workspace_id)
        uow.documents.save_admitted(workspace_id, cv)
        uow.conversations.create_conversation(workspace_id, conversation_id)
        q = uow.conversations.add_question(
            workspace_id,
            conversation_id=conversation_id,
            question_id=str(uuid.uuid4()),
            client_request_id="hist-1",
            text="question",
        )
        uow.conversations.add_answer(
            workspace_id,
            question_id=q.id,
            answer_id=str(uuid.uuid4()),
            body="answer",
            provider="hermetic",
            model_tag="lexical-hash-v1",
            left_machine=False,
            citation_span_ids=(cv.spans[0].id,),
        )
        uow.commit()

    with uow:
        uow.conversations.hard_delete_history(workspace_id, conversation_id)
        uow.commit()

    with session_factory() as session:
        assert session.execute(text("SELECT count(*) FROM questions")).scalar_one() == 0
        assert session.execute(text("SELECT count(*) FROM answers")).scalar_one() == 0
        assert (
            session.execute(text("SELECT count(*) FROM answer_citations")).scalar_one()
            == 0
        )
