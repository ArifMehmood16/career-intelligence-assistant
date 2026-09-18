"""Issue or refresh the workspace cookie on every API response."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from career_assistant.api.deps import (
    WORKSPACE_COOKIE,
    resolve_workspace_id,
    workspace_cookie_needs_set,
)


class WorkspaceCookieMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        raw = request.cookies.get(WORKSPACE_COOKIE)
        workspace_id = resolve_workspace_id(raw)
        request.state.workspace_id = workspace_id
        response = await call_next(request)
        if workspace_cookie_needs_set(raw, workspace_id):
            response.set_cookie(
                key=WORKSPACE_COOKIE,
                value=workspace_id,
                httponly=True,
                samesite="lax",
                path="/",
            )
        return response
