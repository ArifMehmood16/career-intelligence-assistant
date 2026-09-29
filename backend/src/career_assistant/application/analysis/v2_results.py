"""The reader an app without PostgreSQL uses: it has no v2 analyses to show."""

from __future__ import annotations

from career_assistant.application.ports.search import RetrievalTrace
from career_assistant.application.ports.v2_results import V2RoleResult


class NoV2Results:
    def result(self, workspace_id: str, role_id: str) -> V2RoleResult | None:
        return None

    def traces(
        self, workspace_id: str, role_id: str, requirement_id: str
    ) -> tuple[RetrievalTrace, ...] | None:
        return None
