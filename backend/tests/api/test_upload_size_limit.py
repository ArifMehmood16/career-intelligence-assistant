"""Phase 11.3 — oversized uploads rejected before the body is buffered."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from career_assistant.api.errors import install_exception_handlers
from career_assistant.api.middleware import (
    CorrelationIdMiddleware,
    UploadSizeLimitMiddleware,
)
from career_assistant.api.schemas import ApiModel


class _Echo(ApiModel):
    size: int


def _probe_app(*, max_upload_bytes: int = 64) -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(UploadSizeLimitMiddleware, max_upload_bytes=max_upload_bytes)
    install_exception_handlers(app)
    seen: dict[str, bool] = {"body_read": False}
    app.state.seen = seen

    @app.post("/upload")
    async def upload(request: Request) -> _Echo:
        body = await request.body()
        seen["body_read"] = True
        return _Echo(size=len(body))

    return app


@pytest.mark.anyio
async def test_asgi_rejects_oversized_content_length_without_receive() -> None:
    """Pure ASGI: Content-Length over the limit must not call receive()."""

    async def downstream(scope: object, receive: object, send: object) -> None:
        raise AssertionError("downstream must not run for oversized uploads")

    middleware = UploadSizeLimitMiddleware(downstream, max_upload_bytes=64)
    sent: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        raise AssertionError("request body must not be read")

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/upload",
        "raw_path": b"/upload",
        "query_string": b"",
        "headers": [
            (b"content-length", b"128"),
            (b"content-type", b"application/octet-stream"),
            (b"x-correlation-id", b"corr-upload-1"),
        ],
        "client": ("test", 50000),
        "server": ("test", 80),
    }
    await middleware(scope, receive, send)

    start = next(m for m in sent if m["type"] == "http.response.start")
    assert start["status"] == 413
    body = b"".join(
        m["body"]
        for m in sent
        if m["type"] == "http.response.body"  # type: ignore[misc]
    )
    assert b"document_too_large" in body
    assert b"corr-upload-1" in body


def test_within_limit_upload_reaches_handler() -> None:
    app = _probe_app(max_upload_bytes=64)
    client = TestClient(app)

    response = client.post(
        "/upload",
        content=b"hello",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 200
    assert response.json() == {"size": 5}
    assert app.state.seen["body_read"] is True


def test_create_app_installs_upload_size_limit() -> None:
    from career_assistant.main import create_app

    app = create_app()
    assert any(
        getattr(item, "cls", None) is UploadSizeLimitMiddleware
        for item in app.user_middleware
    )
