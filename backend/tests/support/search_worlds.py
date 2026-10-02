"""Seed chunks for a HybridSearchPort under test, in memory or in PostgreSQL."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker
from tests.integration.conftest import make_document
from tests.support.in_memory_search import (
    EVIDENCE_KINDS,
    ChunkSeed,
    InMemoryHybridSearch,
)

from career_assistant.adapters.persistence.models_v2 import ChunkEmbeddingRow, ChunkRow
from career_assistant.adapters.persistence.search_repos import SqlHybridSearch
from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork
from career_assistant.application.ports.search import HybridSearchPort
from career_assistant.domain.documents import DocumentKind

MODEL_KEY = "test:embed-v1:3:document"
__all__ = [
    "MODEL_KEY",
    "ChunkSeed",
    "InMemoryWorld",
    "SearchWorld",
    "SqlWorld",
]


class SearchWorld(Protocol):
    @property
    def search(self) -> HybridSearchPort: ...

    def workspace(self) -> str: ...

    def document(
        self, workspace_id: str, kind: DocumentKind, *, active: bool
    ) -> str: ...

    def chunk(self, document_id: str, seed: ChunkSeed) -> str: ...


@dataclass
class InMemoryWorld:
    port: InMemoryHybridSearch = field(default_factory=InMemoryHybridSearch)

    @property
    def search(self) -> HybridSearchPort:
        return self.port

    def workspace(self) -> str:
        return str(uuid.uuid4())

    def document(self, workspace_id: str, kind: DocumentKind, *, active: bool) -> str:
        document_id = str(uuid.uuid4())
        self.port.add_document(document_id, workspace_id, kind, active=active)
        return document_id

    def chunk(self, document_id: str, seed: ChunkSeed) -> str:
        chunk_id = str(uuid.uuid4())
        self.port.add_chunk(chunk_id, document_id, seed)
        if seed.vector is not None:
            self.port.add_vector(chunk_id, MODEL_KEY, seed.vector)
        return chunk_id


@dataclass
class SqlWorld:
    session_factory: sessionmaker[Session]
    _workspaces: dict[str, str] = field(default_factory=dict)
    _next_line: dict[str, int] = field(default_factory=dict)

    @property
    def search(self) -> HybridSearchPort:
        return SqlHybridSearch(self.session_factory)

    def workspace(self) -> str:
        workspace_id = str(uuid.uuid4())
        with SqlUnitOfWork(self.session_factory) as uow:
            uow.workspaces.ensure(workspace_id)
            uow.commit()
        return workspace_id

    def document(self, workspace_id: str, kind: DocumentKind, *, active: bool) -> str:
        with SqlUnitOfWork(self.session_factory) as uow:
            stored = uow.documents.save_admitted(
                workspace_id, make_document(kind=kind, is_active=active)
            )
            uow.commit()
        self._workspaces[stored.id] = workspace_id
        return stored.id

    def chunk(self, document_id: str, seed: ChunkSeed) -> str:
        line = self._next_line.get(document_id, 1)
        self._next_line[document_id] = line + 1
        workspace_id = uuid.UUID(self._workspaces[document_id])
        row = ChunkRow(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            document_id=uuid.UUID(document_id),
            first_line=line,
            last_line=line,
            start_offset=0,
            end_offset=len(seed.text),
            kind=seed.kind,
            text=seed.text,
            context=seed.context,
            tech_terms=[t.casefold() for t in seed.tech_terms],
            evidence_eligible=seed.kind in EVIDENCE_KINDS,
            chunker_provider="test",
            chunker_model="test",
            prompt_version="test",
        )
        with self.session_factory() as session:
            session.add(row)
            session.flush()
            if seed.vector is not None:
                session.add(
                    ChunkEmbeddingRow(
                        workspace_id=workspace_id,
                        chunk_id=row.id,
                        model_key=MODEL_KEY,
                        provider="test",
                        model_tag="embed-v1",
                        dimensions=len(seed.vector),
                        input_type="document",
                        embedding=list(seed.vector),
                    )
                )
            session.commit()
        return str(row.id)
