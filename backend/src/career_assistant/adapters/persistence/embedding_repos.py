"""SQL adapter for the embedding cache port."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable, Sequence
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from career_assistant.adapters.persistence.models import EmbeddingRow


def _as_uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def _as_vector(value: object) -> tuple[float, ...]:
    """Accept a list or a driver array.

    pgvector returns a numpy array when numpy is installed. That array is
    iterable, but it is not a ``Sequence``, and its scalars are not ``float``.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise TypeError("embedding is not a numeric sequence")
    return tuple(_component(item) for item in value)


def _component(item: object) -> float:
    if isinstance(item, bool) or isinstance(item, (str, bytes)):
        raise TypeError("embedding component is not numeric")
    if isinstance(item, (int, float)):
        return float(item)
    convert = getattr(item, "__float__", None)
    if not callable(convert):
        raise TypeError("embedding component is not numeric")
    try:
        return float(convert())
    except (TypeError, ValueError) as exc:
        raise TypeError("embedding component is not numeric") from exc


class SqlEmbeddingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(
        self,
        workspace_id: str,
        *,
        owner_kind: str,
        owner_id: str,
        provider: str,
        model_tag: str,
        text_sha256: str,
    ) -> tuple[float, ...] | None:
        try:
            owner_uuid = _as_uuid(owner_id)
        except ValueError:
            return None
        row = self._session.scalar(
            select(EmbeddingRow).where(
                EmbeddingRow.workspace_id == _as_uuid(workspace_id),
                EmbeddingRow.owner_kind == owner_kind,
                EmbeddingRow.owner_id == owner_uuid,
                EmbeddingRow.provider == provider,
                EmbeddingRow.model_tag == model_tag,
                EmbeddingRow.text_sha256 == text_sha256,
            )
        )
        if row is None:
            return None
        return _as_vector(row.embedding)

    def put(
        self,
        workspace_id: str,
        *,
        owner_kind: str,
        owner_id: str,
        provider: str,
        model_tag: str,
        text_sha256: str,
        dimensions: int,
        vector: tuple[float, ...],
    ) -> None:
        owner_uuid = _as_uuid(owner_id)
        existing = self._session.scalar(
            select(EmbeddingRow).where(
                EmbeddingRow.workspace_id == _as_uuid(workspace_id),
                EmbeddingRow.owner_kind == owner_kind,
                EmbeddingRow.owner_id == owner_uuid,
                EmbeddingRow.provider == provider,
                EmbeddingRow.model_tag == model_tag,
                EmbeddingRow.text_sha256 == text_sha256,
            )
        )
        if existing is not None:
            existing.dimensions = dimensions
            existing.embedding = list(vector)
            self._session.flush()
            return
        self._session.add(
            EmbeddingRow(
                workspace_id=_as_uuid(workspace_id),
                owner_kind=owner_kind,
                owner_id=owner_uuid,
                provider=provider,
                model_tag=model_tag,
                dimensions=dimensions,
                text_sha256=text_sha256,
                embedding=list(vector),
            )
        )
        self._session.flush()

    def delete_for_workspace(self, workspace_id: str) -> None:
        self._session.execute(
            delete(EmbeddingRow).where(
                EmbeddingRow.workspace_id == _as_uuid(workspace_id)
            )
        )
        self._session.flush()

    def delete_for_owners(
        self,
        workspace_id: str,
        *,
        owner_kind: str,
        owner_ids: Sequence[str],
    ) -> None:
        if not owner_ids:
            return
        ids = [_as_uuid(owner_id) for owner_id in owner_ids]
        self._session.execute(
            delete(EmbeddingRow).where(
                EmbeddingRow.workspace_id == _as_uuid(workspace_id),
                EmbeddingRow.owner_kind == owner_kind,
                EmbeddingRow.owner_id.in_(ids),
            )
        )
        self._session.flush()

    def list_for_workspace(self, workspace_id: str) -> tuple[EmbeddingRow, ...]:
        rows = self._session.scalars(
            select(EmbeddingRow).where(
                EmbeddingRow.workspace_id == _as_uuid(workspace_id)
            )
        ).all()
        return tuple(rows)


class _WorkspaceRepo(Protocol):
    def ensure(self, workspace_id: str) -> None: ...


class _EmbeddingUnitOfWork(Protocol):
    embeddings: SqlEmbeddingRepository
    workspaces: _WorkspaceRepo

    def commit(self) -> None: ...

    def __enter__(self) -> _EmbeddingUnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None: ...


class SqlEmbeddingCache:
    """EmbeddingCachePort over PostgreSQL. Opens its own unit of work per call."""

    def __init__(self, uow_factory: Callable[[], _EmbeddingUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def get(
        self,
        workspace_id: str,
        *,
        owner_kind: str,
        owner_id: str,
        provider: str,
        model_tag: str,
        text_sha256: str,
    ) -> tuple[float, ...] | None:
        with self._uow_factory() as uow:
            return uow.embeddings.get(
                workspace_id,
                owner_kind=owner_kind,
                owner_id=owner_id,
                provider=provider,
                model_tag=model_tag,
                text_sha256=text_sha256,
            )

    def put(
        self,
        workspace_id: str,
        *,
        owner_kind: str,
        owner_id: str,
        provider: str,
        model_tag: str,
        text_sha256: str,
        dimensions: int,
        vector: tuple[float, ...],
    ) -> None:
        with self._uow_factory() as uow:
            uow.workspaces.ensure(workspace_id)
            uow.embeddings.put(
                workspace_id,
                owner_kind=owner_kind,
                owner_id=owner_id,
                provider=provider,
                model_tag=model_tag,
                text_sha256=text_sha256,
                dimensions=dimensions,
                vector=vector,
            )
            uow.commit()
