"""HTTP application factory for the Career Intelligence Assistant API.

Routes live under ``/api`` so the web tier can proxy a single prefix and the
browser never holds an API origin. See docs/api-contract.md.
"""

from typing import Literal

from fastapi import APIRouter, FastAPI, Request, Response

from career_assistant.adapters.persistence.readiness import SettingsReadiness
from career_assistant.api.errors import install_exception_handlers
from career_assistant.api.middleware import (
    CorrelationIdMiddleware,
    UploadSizeLimitMiddleware,
    WorkspaceCookieMiddleware,
)
from career_assistant.api.readiness import (
    ReadinessProbe,
    StaticReadiness,
)
from career_assistant.api.routes_cv import router as cv_router
from career_assistant.api.routes_providers import router as providers_router
from career_assistant.api.schemas import ApiModel, ReadyResponse
from career_assistant.application.documents.cv import CvStore, InMemoryCvStore
from career_assistant.settings import LimitSettings, ProviderSettings

router = APIRouter(prefix="/api")


class HealthResponse(ApiModel):
    """Liveness only. It answers with no database and no provider configured."""

    status: Literal["ok"]


@router.get("/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


def _readiness_snapshot(probe: ReadinessProbe) -> StaticReadiness:
    check = getattr(probe, "check", None)
    if callable(check):
        result = check()
        if isinstance(result, StaticReadiness):
            return result
    return StaticReadiness(
        database=probe.database,
        migrations=probe.migrations,
        completion_provider=probe.completion_provider,
        embedding_provider=probe.embedding_provider,
        hosted_egress=probe.hosted_egress,
    )


@router.get("/ready", response_model=ReadyResponse, tags=["ops"])
def ready(request: Request, response: Response) -> ReadyResponse:
    probe: ReadinessProbe | None = getattr(request.app.state, "readiness", None)
    if probe is None:
        probe = SettingsReadiness()
        request.app.state.readiness = probe
    snap = _readiness_snapshot(probe)
    payload = ReadyResponse(
        database=snap.database,
        migrations=snap.migrations,
        completion_provider=snap.completion_provider,
        embedding_provider=snap.embedding_provider,
        hosted_egress=snap.hosted_egress,
    )
    if snap.database != "ok" or snap.migrations != "current":
        response.status_code = 503
    return payload


def create_app(
    *,
    readiness: ReadinessProbe | None = None,
    limits: LimitSettings | None = None,
    providers: ProviderSettings | None = None,
    cv_store: CvStore | None = None,
) -> FastAPI:
    """Build the application. Kept a factory so tests construct their own."""
    upload_limits = limits or LimitSettings()
    app = FastAPI(
        title="Career Intelligence Assistant",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    # Last added runs first for requests.
    app.add_middleware(WorkspaceCookieMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        UploadSizeLimitMiddleware, max_upload_bytes=upload_limits.max_upload_bytes
    )
    install_exception_handlers(app)
    app.state.readiness = readiness
    app.state.limits = upload_limits
    app.state.providers = providers
    app.state.provider_choices = {}
    app.state.cv_store = cv_store if cv_store is not None else InMemoryCvStore()
    app.include_router(router)
    app.include_router(providers_router, prefix="/api")
    app.include_router(cv_router, prefix="/api")
    return app


app = create_app()
