"""A hermetic workspace with one CV and analysed roles, for the MCP tests."""

from __future__ import annotations

from dataclasses import dataclass

from career_assistant.adapters.providers.hermetic.analysis import analyse_hermetic
from career_assistant.application.documents.cv import (
    InMemoryCvStore,
    admission_limits_from,
    upload_pasted_cv,
)
from career_assistant.application.roles.store import InMemoryRoleStore
from career_assistant.settings import LimitSettings

WORKSPACE = "7c2f7a4e-4d7a-4a51-9b8e-1f2a3b4c5d6e"
CV = """Experience
Senior Analytics Engineer — Acme — January 2022 – Present
- Owned dbt models in production for the warehouse.
- Built Looker dashboards for the finance team.
"""
JD = """Requirements
- Must have production dbt experience
- Looker dashboards
"""


@dataclass(frozen=True)
class Workspace:
    cv: InMemoryCvStore
    roles: InMemoryRoleStore
    role_ids: tuple[str, ...]


def analysed_workspace(*titles: str) -> Workspace:
    cv = InMemoryCvStore()
    upload_pasted_cv(
        cv,
        workspace_id=WORKSPACE,
        text=CV,
        filename="cv.txt",
        limits=admission_limits_from(LimitSettings(_env_file=None)),
    )
    roles = InMemoryRoleStore(cv_store=cv, analyser=analyse_hermetic)
    ids = tuple(
        roles.create_role(
            workspace_id=WORKSPACE, title=title, company="Acme", description=JD
        )[0].id
        for title in titles or ("Analytics Engineer",)
    )
    return Workspace(cv, roles, ids)
