"""HTTP application factory for the Career Intelligence Assistant API.

Routes live under ``/api`` so the web tier can proxy a single prefix and the
browser never holds an API origin. See docs/api-contract.md.
"""

from typing import Literal

from fastapi import APIRouter, FastAPI, Request, Response

from career_assistant.adapters.persistence.readiness import SettingsReadiness
from career_assistant.adapters.persistence.wiring import build_sql_stores
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
from career_assistant.api.routes_analysis import router as analysis_router
from career_assistant.api.routes_cv import router as cv_router
from career_assistant.api.routes_documents import router as documents_router
from career_assistant.api.routes_messages import router as messages_router
from career_assistant.api.routes_providers import router as providers_router
from career_assistant.api.routes_roles import router as roles_router
from career_assistant.api.routes_spans import router as spans_router
from career_assistant.api.schemas import ApiModel, ReadyResponse
from career_assistant.application.documents.cv import CvStore, InMemoryCvStore
from career_assistant.application.documents.supporting import (
    InMemorySupportingDocumentStore,
    SupportingDocumentStore,
)
from career_assistant.application.roles.store import InMemoryRoleStore
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
    role_store: object | None = None,
    supporting_store: SupportingDocumentStore | None = None,
) -> FastAPI:
    """Build the application. Kept a factory so tests construct their own.

    Default stores are in-memory for hermetic API tests. The module-level
    ``app`` used by uvicorn/Docker is built with ``create_production_app``.
    """
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
    resolved_cv = cv_store if cv_store is not None else InMemoryCvStore()
    app.state.cv_store = resolved_cv
    app.state.role_store = (
        role_store
        if role_store is not None
        else InMemoryRoleStore(cv_store=resolved_cv)
    )
    app.state.supporting_store = (
        supporting_store
        if supporting_store is not None
        else InMemorySupportingDocumentStore(cv_store=resolved_cv)
    )
    app.include_router(router)
    app.include_router(providers_router, prefix="/api")
    app.include_router(cv_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(spans_router, prefix="/api")
    app.include_router(roles_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api")
    app.include_router(messages_router, prefix="/api")
    return app


def create_production_app(
    *,
    readiness: ReadinessProbe | None = None,
    limits: LimitSettings | None = None,
    providers: ProviderSettings | None = None,
) -> FastAPI:
    """Wire SQL stores for the process entrypoint (uvicorn / Docker CMD)."""
    cv_store, role_store, supporting_store = build_sql_stores()
    return create_app(
        readiness=readiness if readiness is not None else SettingsReadiness(),
        limits=limits,
        providers=providers,
        cv_store=cv_store,
        role_store=role_store,
        supporting_store=supporting_store,
    )


app = create_production_app()
