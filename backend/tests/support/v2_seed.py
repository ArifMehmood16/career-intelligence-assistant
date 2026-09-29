"""Seed one workspace with a row in every v2 table (PLAN 18.3).

Raw SQL on purpose, so schema tests pin what the database guarantees on its own.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.conftest import make_document

from career_assistant.adapters.persistence.schema import APP_SCHEMA
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.domain.documents import DocumentKind


@dataclass(frozen=True)
class Seeded:
    workspace: str
    cv: str
    jd: str
    cv_chunk: str
    jd_chunk: str
    verdict: str


def insert_row(session: Session, table: str, **values: object) -> str:
    row_id = str(values.setdefault("id", uuid.uuid4()))
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    session.execute(
        text(f"INSERT INTO {APP_SCHEMA}.{table} ({columns}) VALUES ({placeholders})"),
        {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in values.items()},
    )
    return row_id


def insert_chunk(
    session: Session, ws: str, doc: str, kind: str, body: str, **extra: object
) -> str:
    return insert_row(
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


def seed_v2(uow: SqlUnitOfWork, session_factory: sessionmaker[Session]) -> Seeded:
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
        role = insert_row(
            session,
            "roles",
            workspace_id=ws,
            title="AI Engineer",
            company="Acme",
            job_description_document_id=jd.id,
            analysis_version=1,
            status="ready",
        )
        job = insert_row(
            session,
            "analysis_jobs",
            workspace_id=ws,
            role_id=role,
            kind="role_analysis",
            state="succeeded",
        )
        cv_chunk = insert_chunk(
            session,
            ws,
            cv.id,
            "experience",
            "Built hybrid retrieval over pgvector.",
            context="Senior Data Engineer at Northwind",
            tech_terms=["pgvector"],
        )
        jd_chunk = insert_chunk(session, ws, jd.id, "requirement", "5+ years of Python")
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
        requirement = insert_row(
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
        tech = insert_row(
            session,
            "kg_nodes",
            workspace_id=ws,
            document_id=cv.id,
            kind="technology",
            canonical_name="pgvector",
        )
        category = insert_row(
            session,
            "kg_nodes",
            workspace_id=ws,
            document_id=cv.id,
            kind="category",
            canonical_name="vector database",
        )
        role_node = insert_row(
            session,
            "kg_nodes",
            workspace_id=ws,
            document_id=cv.id,
            kind="role",
            canonical_name="senior data engineer",
        )
        insert_row(
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
        insert_row(
            session,
            "kg_edges",
            workspace_id=ws,
            document_id=cv.id,
            source_id=tech,
            target_id=category,
            relation="IS_A",
            provenance="inferred",
        )
        verdict = insert_row(
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
        insert_row(
            session,
            "verdict_evidence",
            workspace_id=ws,
            verdict_id=verdict,
            chunk_id=cv_chunk,
            dimension="match",
            quote="hybrid retrieval",
        )
        insert_row(
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
    return Seeded(
        workspace=ws,
        cv=cv.id,
        jd=jd.id,
        cv_chunk=cv_chunk,
        jd_chunk=jd_chunk,
        verdict=verdict,
    )
