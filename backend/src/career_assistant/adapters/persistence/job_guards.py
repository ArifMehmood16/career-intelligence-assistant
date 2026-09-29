"""Checks a running analysis makes before it writes (v1 and v2 workers)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class JobCancelled(Exception):
    """The role was deleted while its analysis was still running."""


class DocumentReader(Protocol):
    def get(self, workspace_id: str, document_id: str) -> object | None: ...


class RoleReader(Protocol):
    def get(self, workspace_id: str, role_id: str) -> object | None: ...


def require_role(roles: RoleReader, workspace_id: str, role_id: str) -> None:
    """A deleted role is a cancellation, not an analysis failure.

    Hard delete removes the role, its job rows and its job description. The
    worker may already be past extraction. Writing spans then fails a foreign
    key, and recording that failure fails because the job row is gone too.
    """
    if roles.get(workspace_id, role_id) is None:
        raise JobCancelled(role_id)


def require_documents(
    documents: DocumentReader,
    workspace_id: str,
    document_ids: Sequence[str],
) -> None:
    """Fail by name when an upload the analysis started from has gone.

    Extraction runs for minutes between reading a document and writing its
    spans, and a replaced or deleted upload takes its row with it. Writing
    anyway raised a foreign-key violation from the driver, which says nothing
    about what happened.
    """
    missing = [
        document_id
        for document_id in document_ids
        if documents.get(workspace_id, document_id) is None
    ]
    if missing:
        raise RuntimeError("documents_changed")
