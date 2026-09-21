"""Workspace-scoped span lookup — CV, supporting letters and role JD spans."""

from __future__ import annotations

from career_assistant.application.documents.cv import CvStore
from career_assistant.application.documents.supporting import SupportingDocumentStore
from career_assistant.domain.documents import Page, Span


def lookup_workspace_span(
    workspace_id: str,
    span_id: str,
    *,
    cv_store: CvStore,
    supporting_store: SupportingDocumentStore | None = None,
    role_store: object | None = None,
) -> tuple[Span, tuple[Page, ...]] | None:
    """Resolve a citation against every document kind in the workspace."""
    found = cv_store.get_span(workspace_id, span_id)
    if found is not None:
        return found
    if supporting_store is not None:
        found = supporting_store.get_span(workspace_id, span_id)
        if found is not None:
            return found
    getter = getattr(role_store, "get_span", None)
    if callable(getter):
        found = getter(workspace_id, span_id)
        if found is not None:
            return found
    return None
