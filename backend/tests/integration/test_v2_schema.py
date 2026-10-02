"""The v2 schema: chunks, vectors, the knowledge graph and verdicts (PLAN 18.3).

Raw SQL on purpose: these tests pin what the database guarantees on its own —
generated columns, constraints, row-level security and cascades — whatever the
repositories built on top of it later do.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.support.v2_seed import Seeded, insert_chunk, insert_row

from career_assistant.adapters.persistence.schema import APP_SCHEMA
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork

pytestmark = pytest.mark.integration

V2_TABLES = (
    "chunks",
    "chunk_embeddings",
    "requirement_items",
    "kg_nodes",
    "kg_edges",
    "match_verdicts",
    "verdict_evidence",
    "retrieval_traces",
)
# Rows that must not survive deleting the CV they came from.
CV_DERIVED = {
    "chunks": "document_id = CAST(:cv AS uuid)",
    "chunk_embeddings": "chunk_id = CAST(:cv_chunk AS uuid)",
    "kg_nodes": "document_id = CAST(:cv AS uuid)",
    "kg_edges": "document_id = CAST(:cv AS uuid)",
    "match_verdicts": "workspace_id = CAST(:ws AS uuid)",
    "verdict_evidence": "workspace_id = CAST(:ws AS uuid)",
    "retrieval_traces": "workspace_id = CAST(:ws AS uuid)",
}


def _q(session: Session, sql: str, **params: object) -> object:
    return session.execute(text(sql), params).scalar()


def test_the_v2_tables_live_in_the_application_schema(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        present = {
            row[0]
            for row in session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = :s"
                ),
                {"s": APP_SCHEMA},
            )
        }
    assert set(V2_TABLES) <= present


def test_pgvector_lives_in_the_extensions_schema(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        schema = _q(
            session,
            "SELECT extnamespace::regnamespace::text FROM pg_extension "
            "WHERE extname = 'vector'",
        )
    assert schema == "extensions"


def test_every_application_table_has_row_level_security(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        without = (
            session.execute(
                text(
                    "SELECT c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = :s AND c.relkind = 'r' AND NOT c.relrowsecurity "
                    "AND c.relname <> 'alembic_version'"
                ),
                {"s": APP_SCHEMA},
            )
            .scalars()
            .all()
        )
    assert without == []


def test_a_role_without_policies_reads_no_rows(
    seeded: Seeded, session_factory: sessionmaker[Session]
) -> None:
    probe = f"rls_probe_{uuid.uuid4().hex[:8]}"
    with session_factory() as session:
        session.execute(text(f"CREATE ROLE {probe} NOLOGIN NOBYPASSRLS"))
        session.execute(text(f"GRANT USAGE ON SCHEMA {APP_SCHEMA} TO {probe}"))
        session.execute(
            text(f"GRANT SELECT ON ALL TABLES IN SCHEMA {APP_SCHEMA} TO {probe}")
        )
        owner_sees = _q(session, f"SELECT count(*) FROM {APP_SCHEMA}.chunks")
        session.execute(text(f"SET LOCAL ROLE {probe}"))
        probe_sees = _q(session, f"SELECT count(*) FROM {APP_SCHEMA}.chunks")
        # Roles and grants are transactional: rolling back leaves nothing behind.
        session.rollback()
    assert owner_sees == 2
    assert probe_sees == 0


def test_full_text_is_generated_and_left_empty_for_contact_chunks(
    seeded: Seeded, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        contact = insert_chunk(
            session,
            seeded.workspace,
            seeded.cv,
            "contact",
            "jane@example.com",
            first_line=9,
            last_line=9,
        )
        found = _q(
            session,
            f"SELECT count(*) FROM {APP_SCHEMA}.chunks "
            "WHERE fts @@ to_tsquery('english', 'retrieval')",
        )
        contact_fts = _q(
            session,
            f"SELECT fts IS NULL FROM {APP_SCHEMA}.chunks WHERE id = CAST(:id AS uuid)",
            id=contact,
        )
        session.rollback()
    assert found == 1
    assert contact_fts is True


@pytest.mark.parametrize(
    ("provenance", "cites_chunk"),
    [("asserted", False), ("inferred", True)],
    ids=["asserted-without-citation", "inferred-with-citation"],
)
def test_an_edge_cites_a_chunk_exactly_when_it_is_asserted(
    seeded: Seeded,
    session_factory: sessionmaker[Session],
    provenance: str,
    cites_chunk: bool,
) -> None:
    with session_factory() as session:
        nodes = (
            session.execute(
                text(
                    f"SELECT id FROM {APP_SCHEMA}.kg_nodes "
                    "WHERE document_id = CAST(:d AS uuid) LIMIT 2"
                ),
                {"d": seeded.cv},
            )
            .scalars()
            .all()
        )
        with pytest.raises(IntegrityError):
            insert_row(
                session,
                "kg_edges",
                workspace_id=seeded.workspace,
                document_id=seeded.cv,
                source_id=nodes[0],
                target_id=nodes[1],
                relation="USED",
                provenance=provenance,
                chunk_id=seeded.cv_chunk if cites_chunk else None,
            )
            session.flush()
        session.rollback()


@pytest.mark.parametrize(
    "column", ["match_score", "seniority_score", "experience_score"]
)
def test_a_judge_score_outside_zero_to_four_is_refused(
    seeded: Seeded, session_factory: sessionmaker[Session], column: str
) -> None:
    with session_factory() as session:
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    f"UPDATE {APP_SCHEMA}.match_verdicts SET {column} = 5 "
                    "WHERE id = CAST(:v AS uuid)"
                ),
                {"v": seeded.verdict},
            )
            session.flush()
        session.rollback()


def test_deleting_the_cv_removes_every_row_derived_from_it(
    seeded: Seeded, uow: SqlUnitOfWork, session_factory: sessionmaker[Session]
) -> None:
    with uow:
        uow.documents.hard_delete(seeded.workspace, seeded.cv)
        uow.commit()

    params = {"cv": seeded.cv, "cv_chunk": seeded.cv_chunk, "ws": seeded.workspace}
    with session_factory() as session:
        survivors = {
            table: _q(
                session,
                f"SELECT count(*) FROM {APP_SCHEMA}.{table} WHERE {where}",
                **params,
            )
            for table, where in CV_DERIVED.items()
        }
        jd_chunks = _q(
            session,
            f"SELECT count(*) FROM {APP_SCHEMA}.chunks "
            "WHERE document_id = CAST(:d AS uuid)",
            d=seeded.jd,
        )
        requirements = _q(
            session,
            f"SELECT count(*) FROM {APP_SCHEMA}.requirement_items "
            "WHERE workspace_id = CAST(:ws AS uuid)",
            ws=seeded.workspace,
        )
    assert survivors == dict.fromkeys(CV_DERIVED, 0)
    assert jd_chunks == 1
    assert requirements == 1


def test_deleting_the_workspace_removes_every_v2_row(
    seeded: Seeded, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.execute(
            text(f"DELETE FROM {APP_SCHEMA}.workspaces WHERE id = CAST(:ws AS uuid)"),
            {"ws": seeded.workspace},
        )
        session.commit()
        counts = {
            table: _q(session, f"SELECT count(*) FROM {APP_SCHEMA}.{table}")
            for table in V2_TABLES
        }
    assert counts == dict.fromkeys(V2_TABLES, 0)
