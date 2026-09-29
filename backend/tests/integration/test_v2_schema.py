"""The v2 schema: chunks, vectors, the knowledge graph and verdicts (PLAN 18.3).

Raw SQL on purpose: these tests pin what the database guarantees on its own —
generated columns, constraints, row-level security and cascades — whatever the
repositories built on top of it later do.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.conftest import make_document

from career_assistant.adapters.persistence.schema import APP_SCHEMA
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.domain.documents import DocumentKind

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


@dataclass(frozen=True)
class Seeded:
    workspace: str
    cv: str
    jd: str
    cv_chunk: str
    jd_chunk: str
    verdict: str


def _q(session: Session, sql: str, **params: object) -> object:
    return session.execute(text(sql), params).scalar()


def _insert(session: Session, table: str, **values: object) -> str:
    row_id = str(values.setdefault("id", uuid.uuid4()))
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    session.execute(
        text(f"INSERT INTO {APP_SCHEMA}.{table} ({columns}) VALUES ({placeholders})"),
        {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in values.items()},
    )
    return row_id


def _chunk(
    session: Session, ws: str, doc: str, kind: str, body: str, **extra: object
) -> str:
    return _insert(
        session,
        "chunks",
        workspace_id=ws,
        document_id=doc,
        first_line=extra.pop("first_line", 1),
        last_line=extra.pop("last_line", 1),
        start_offset=0,
        end_offset=len(body),
        kind=kind,
        text=body,
        evidence_eligible=kind in {"experience", "project", "skills", "qualification"},
        chunker_provider="hermetic",
        chunker_model="rules-v1",
        prompt_version="cv-chunking-v1",
        **extra,
    )


@pytest.fixture()
def seeded(
    uow: SqlUnitOfWork, session_factory: sessionmaker[Session]
) -> Iterator[Seeded]:
    ws = str(uuid.uuid4())
    with uow:
        uow.workspaces.ensure(ws)
        cv = uow.documents.save_admitted(
            ws, make_document(text="Built hybrid retrieval.")
        )
        jd = uow.documents.save_admitted(
            ws,
            make_document(
                kind=DocumentKind.JOB_DESCRIPTION,
                text="5+ years of Python",
                is_active=False,
            ),
        )
        uow.commit()
    with session_factory() as session:
        role = _insert(
            session,
            "roles",
            workspace_id=ws,
            title="AI Engineer",
            company="Acme",
            job_description_document_id=jd.id,
            analysis_version=1,
            status="ready",
        )
        job = _insert(
            session,
            "analysis_jobs",
            workspace_id=ws,
            role_id=role,
            kind="role_analysis",
            state="succeeded",
        )
        cv_chunk = _chunk(
            session,
            ws,
            cv.id,
            "experience",
            "Built hybrid retrieval over pgvector.",
            context="Senior Data Engineer at Northwind",
            tech_terms=["pgvector"],
        )
        jd_chunk = _chunk(session, ws, jd.id, "requirement", "5+ years of Python")
        session.execute(
            text(
                f"INSERT INTO {APP_SCHEMA}.chunk_embeddings "
                "(id, workspace_id, chunk_id, model_key, provider, model_tag, "
                "dimensions, input_type, embedding) VALUES (:id, :ws, :chunk, "
                "'hermetic:lexical-hash-v1:3:document', 'hermetic', "
                "'lexical-hash-v1', 3, 'document', '[0.1, 0.2, 0.3]')"
            ),
            {"id": str(uuid.uuid4()), "ws": ws, "chunk": cv_chunk},
        )
        requirement = _insert(
            session,
            "requirement_items",
            workspace_id=ws,
            role_id=role,
            chunk_id=jd_chunk,
            position=0,
            quote="5+ years of Python",
            statement="5+ years of Python",
            must_have=True,
            years_expected=5.0,
        )
        tech = _insert(
            session,
            "kg_nodes",
            workspace_id=ws,
            document_id=cv.id,
            kind="technology",
            canonical_name="pgvector",
        )
        category = _insert(
            session,
            "kg_nodes",
            workspace_id=ws,
            document_id=cv.id,
            kind="category",
            canonical_name="vector database",
        )
        role_node = _insert(
            session,
            "kg_nodes",
            workspace_id=ws,
            document_id=cv.id,
            kind="role",
            canonical_name="senior data engineer",
        )
        _insert(
            session,
            "kg_edges",
            workspace_id=ws,
            document_id=cv.id,
            source_id=role_node,
            target_id=tech,
            relation="USED",
            provenance="asserted",
            chunk_id=cv_chunk,
        )
        _insert(
            session,
            "kg_edges",
            workspace_id=ws,
            document_id=cv.id,
            source_id=tech,
            target_id=category,
            relation="IS_A",
            provenance="inferred",
        )
        verdict = _insert(
            session,
            "match_verdicts",
            workspace_id=ws,
            analysis_id=job,
            requirement_item_id=requirement,
            verdict="partial",
            match_score=3,
            seniority_score=None,
            experience_score=1,
            payload='{"rationale": "Built hybrid retrieval"}',
            input_hash="a" * 64,
            provider="hermetic",
            model_tag="rules-v1",
            prompt_version="judge-v1",
            contract_version="judge-v1",
        )
        _insert(
            session,
            "verdict_evidence",
            workspace_id=ws,
            verdict_id=verdict,
            chunk_id=cv_chunk,
            dimension="match",
            quote="hybrid retrieval",
        )
        _insert(
            session,
            "retrieval_traces",
            workspace_id=ws,
            verdict_id=verdict,
            round=0,
            query_text="5+ years of Python",
            chunk_id=cv_chunk,
            dense_rank=1,
            lexical_rank=None,
            exact_rank=None,
            fused_score=0.016,
        )
        session.commit()
    yield Seeded(
        workspace=ws,
        cv=cv.id,
        jd=jd.id,
        cv_chunk=cv_chunk,
        jd_chunk=jd_chunk,
        verdict=verdict,
    )


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
        contact = _chunk(
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
            _insert(
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
