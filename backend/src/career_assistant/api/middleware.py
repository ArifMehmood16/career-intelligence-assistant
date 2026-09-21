"""Cross-cutting HTTP middleware for workspace, correlation and upload limits."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from career_assistant.api.deps import (
    CORRELATION_HEADER,
    WORKSPACE_COOKIE,
    resolve_correlation_id,
    resolve_workspace_id,
    workspace_cookie_needs_set,
)
from career_assistant.logconfig import (
    bind_request_context,
    clear_request_context,
    log_event,
)

_UPLOAD_METHODS = frozenset({"POST", "PUT", "PATCH"})
_http_log = logging.getLogger("career_assistant.http")


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


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = resolve_correlation_id(request.headers.get(CORRELATION_HEADER))
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status and duration — never the body."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = getattr(request.state, "correlation_id", "-")
        workspace_id = getattr(request.state, "workspace_id", None)
        bind_request_context(
            correlation_id=str(correlation_id),
            workspace_id=str(workspace_id) if workspace_id else None,
        )
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - started) * 1000)
            log_event(
                _http_log,
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
            )
            raise
        else:
            duration_ms = int((time.perf_counter() - started) * 1000)
            log_event(
                _http_log,
                "request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
            )
            return response
        finally:
            clear_request_context()


class UploadSizeLimitMiddleware:
    """Reject oversized bodies using Content-Length — never buffer them first."""

    def __init__(self, app: ASGIApp, *, max_upload_bytes: int) -> None:
        self.app = app
        self.max_upload_bytes = max_upload_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in _UPLOAD_METHODS:
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_length = headers.get(b"content-length")
        if raw_length is None:
            await self.app(scope, receive, send)
            return

        try:
            content_length = int(raw_length.decode("ascii"))
        except ValueError, UnicodeDecodeError:
            await self.app(scope, receive, send)
            return

        if content_length <= self.max_upload_bytes:
            await self.app(scope, receive, send)
            return

        correlation_id = resolve_correlation_id(
            headers.get(b"x-correlation-id", b"").decode("ascii", errors="ignore")
            or None
        )
        log_event(
            _http_log,
            "http.error",
            status=413,
            code="document_too_large",
            path=scope.get("path"),
            content_length=content_length,
        )
        payload = json.dumps(
            {
                "error": {
                    "code": "document_too_large",
                    "message": "Document exceeds the configured upload size limit.",
                    "correlationId": correlation_id,
                }
            }
        ).encode("utf-8")

        async def send_reject(message: Message) -> None:
            await send(message)

        await send_reject(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode("ascii")),
                    (
                        CORRELATION_HEADER.lower().encode("ascii"),
                        correlation_id.encode("ascii"),
                    ),
                ],
            }
        )
        await send_reject({"type": "http.response.body", "body": payload})
