"""Workspace identity from the ``workspace`` cookie — no auth yet."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Request, Response

WORKSPACE_COOKIE = "workspace"


def resolve_workspace_id(raw: str | None) -> str:
    """Return a valid workspace UUID, minting one when missing or invalid."""
    if raw is None:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(raw))
    except ValueError:
        return str(uuid.uuid4())


def workspace_cookie_needs_set(raw: str | None, resolved: str) -> bool:
    return raw != resolved


async def get_workspace_id(
    request: Request,
    response: Response,
    workspace: Annotated[str | None, Cookie(alias=WORKSPACE_COOKIE)] = None,
) -> str:
    """FastAPI dependency for routes that must scope by workspace."""
    # Prefer middleware-resolved value when present so cookie and dependency agree.
    state_value = getattr(request.state, "workspace_id", None)
    if isinstance(state_value, str) and state_value:
        return state_value
    resolved = resolve_workspace_id(workspace)
    if workspace_cookie_needs_set(workspace, resolved):
        response.set_cookie(
            key=WORKSPACE_COOKIE,
            value=resolved,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return resolved


WorkspaceId = Annotated[str, Depends(get_workspace_id)]
