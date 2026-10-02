"""The tool registry over a whole workspace, for a caller with no ask request.

The MCP server has no question and no retrieved pool, so it reads what an ask
request would: every analysed role and the workspace's spans. It is read again on
each call, so an MCP client sees a role as soon as its analysis is ready.
"""

from __future__ import annotations

from typing import Protocol

from career_assistant.application.ask.registry import ToolRegistry, evidence_registry
from career_assistant.application.ask.views import role_analysis_view
from career_assistant.application.documents.cv import CvStore
from career_assistant.application.documents.supporting import SupportingDocumentStore
from career_assistant.application.intake.workspace_spans import retrieval_pool
from career_assistant.application.roles.analysis import AnalysisBundle
from career_assistant.application.roles.store import RoleOperationRejected, RoleView
from career_assistant.domain.ask import RoleAnalysisView
from career_assistant.domain.documents import Page, Span
from career_assistant.domain.prompts import RetrievedSpan


class WorkspaceRoles(Protocol):
    def list_roles(self, workspace_id: str) -> tuple[RoleView, ...]: ...

    def require_analysis(self, workspace_id: str, role_id: str) -> AnalysisBundle: ...

    def job_description_spans(self, workspace_id: str) -> tuple[RetrievedSpan, ...]: ...

    def get_span(
        self, workspace_id: str, span_id: str
    ) -> tuple[Span, tuple[Page, ...]] | None: ...


def workspace_registry(
    workspace_id: str,
    *,
    roles: WorkspaceRoles,
    cv_store: CvStore,
    supporting_store: SupportingDocumentStore | None = None,
) -> ToolRegistry:
    return evidence_registry(
        _analysed(workspace_id, roles),
        retrieval_pool(
            workspace_id,
            cv_store=cv_store,
            supporting_store=supporting_store,
            role_store=roles,
        ),
    )


def _analysed(workspace_id: str, roles: WorkspaceRoles) -> tuple[RoleAnalysisView, ...]:
    """Ready roles only; one still analysing or failed has nothing to cite yet."""
    views: list[RoleAnalysisView] = []
    for role in roles.list_roles(workspace_id):
        if role.status != "ready":
            continue
        try:
            bundle = roles.require_analysis(workspace_id, role.id)
        except RoleOperationRejected:
            continue  # Re-analysed or deleted between the two reads.
        views.append(
            role_analysis_view(role_id=role.id, title=role.title, bundle=bundle)
        )
    return tuple(views)
