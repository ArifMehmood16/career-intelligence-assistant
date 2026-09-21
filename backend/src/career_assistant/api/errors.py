"""Safe HTTP error mapping — contract codes only, no internal leakage."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from career_assistant.api.deps import resolve_correlation_id
from career_assistant.api.schemas import ErrorBody, ErrorEnvelope
from career_assistant.logconfig import log_event

_SAFE_INTERNAL_MESSAGE = "Something went wrong."
_SAFE_VALIDATION_MESSAGE = "Request failed validation."
_error_log = logging.getLogger("career_assistant.http")


class AppError(Exception):
    """Domain/application failure already mapped to a contract error code."""

    def __init__(self, code: str, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _correlation_id(request: Request) -> str:
    state_value = getattr(request.state, "correlation_id", None)
    if isinstance(state_value, str) and state_value:
        return state_value
    return resolve_correlation_id(request.headers.get("X-Correlation-Id"))


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    correlation_id: str,
) -> JSONResponse:
    envelope = ErrorEnvelope(
        error=ErrorBody(code=code, message=message, correlation_id=correlation_id)
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(by_alias=True),
        headers={"X-Correlation-Id": correlation_id},
    )


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        log_event(
            _error_log,
            "http.error",
            status=exc.status_code,
            code=exc.code,
            path=request.url.path,
        )
        return error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            correlation_id=_correlation_id(request),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        log_event(
            _error_log,
            "http.error",
            status=422,
            code="validation_failed",
            path=request.url.path,
        )
        return error_response(
            status_code=422,
            code="validation_failed",
            message=_SAFE_VALIDATION_MESSAGE,
            correlation_id=_correlation_id(request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, str) and detail and " " not in detail:
            code = detail
            message = detail.replace("_", " ")
        else:
            code = "internal_error" if exc.status_code >= 500 else "validation_failed"
            message = (
                _SAFE_INTERNAL_MESSAGE
                if exc.status_code >= 500
                else _SAFE_VALIDATION_MESSAGE
            )
        log_event(
            _error_log,
            "http.error",
            status=exc.status_code,
            code=code,
            path=request.url.path,
        )
        return error_response(
            status_code=exc.status_code,
            code=code,
            message=message,
            correlation_id=_correlation_id(request),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, _exc: Exception) -> JSONResponse:
        log_event(
            _error_log,
            "http.error",
            status=500,
            code="internal_error",
            path=request.url.path,
            exc_type=type(_exc).__name__,
        )
        return error_response(
            status_code=500,
            code="internal_error",
            message=_SAFE_INTERNAL_MESSAGE,
            correlation_id=_correlation_id(request),
        )
