"""HTTP application factory for the Career Intelligence Assistant API.

Routes live under ``/api`` so the web tier can proxy a single prefix and the
browser never holds an API origin. See docs/api-contract.md.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import APIRouter, FastAPI, Request, Response

from career_assistant.adapters.extraction.selected import extractors_for_choice
from career_assistant.adapters.persistence.accounting import SqlCallAccountant
from career_assistant.adapters.persistence.analysis_worker import SqlAnalysisWorker
from career_assistant.adapters.persistence.conversation_store import (
    SqlConversationStore,
)
from career_assistant.adapters.persistence.readiness import SettingsReadiness
from career_assistant.adapters.persistence.wiring import build_sql_stores
from career_assistant.api.errors import install_exception_handlers
from career_assistant.api.middleware import (
    CorrelationIdMiddleware,
    RequestLoggingMiddleware,
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
from career_assistant.application.ask.memory import InMemoryConversationStore
from career_assistant.application.ask.service import ConversationStore
from career_assistant.application.documents.cv import CvStore, InMemoryCvStore
from career_assistant.application.documents.supporting import (
    InMemorySupportingDocumentStore,
    SupportingDocumentStore,
)
from career_assistant.application.ports.extraction import (
    ClaimExtractionPort,
    RequirementExtractionPort,
)
from career_assistant.application.providers.accounting import CallAccountant
from career_assistant.application.providers.catalogue import default_provider_choice
from career_assistant.application.providers.choice_store import (
    InMemoryProviderChoiceStore,
    ProviderChoiceStore,
)
from career_assistant.application.roles.store import ExtractorFactory, InMemoryRoleStore
from career_assistant.logconfig import configure_logging, load_secret_values, log_event
from career_assistant.settings import (
    DatabaseSettings,
    LimitSettings,
    LoggingSettings,
    ProviderSettings,
)

router = APIRouter(prefix="/api")


def _configure_process_logging(
    *,
    force: bool,
    extra_secrets: tuple[str, ...] = (),
) -> None:
    settings = LoggingSettings()
    configure_logging(
        force=force,
        secret_values=load_secret_values() + extra_secrets,
        log_file=settings.log_file,
        level=settings.resolved_level(),
        max_bytes=settings.log_file_max_bytes,
        backup_count=settings.log_file_backup_count,
    )


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    providers = getattr(app.state, "providers", None)
    extra_secrets: tuple[str, ...] = ()
    if isinstance(providers, ProviderSettings):
        extra_secrets = providers.secret_values()
    _configure_process_logging(force=True, extra_secrets=extra_secrets)
    log_event(
        logging.getLogger("career_assistant.config"),
        "process_start",
        **_safe_process_fields(app),
    )
    worker = getattr(app.state, "analysis_worker", None)
    if worker is None:
        yield
        return
    stop = threading.Event()
    thread = threading.Thread(
        target=worker.run_forever,
        kwargs={"stop": stop},
        name="analysis-worker",
        daemon=True,
    )
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=5.0)


def _safe_process_fields(app: FastAPI) -> dict[str, object]:
    providers = getattr(app.state, "providers", None)
    database = DatabaseSettings()
    fields: dict[str, object] = {
        "sql_stores": type(getattr(app.state, "cv_store", None)).__name__,
        "database_host": database.host_path_hostname(),
        "database_port": database.host_path_port(),
    }
    if isinstance(providers, ProviderSettings):
        snap = providers.public_snapshot()
        fields["completion_provider"] = snap["completionProvider"]
        fields["embedding_provider"] = snap["embeddingProvider"]
        fields["hosted_egress"] = snap["allowHostedProviders"]
        fields["openai_key_configured"] = snap["openaiKeyConfigured"]
        fields["anthropic_key_configured"] = snap["anthropicKeyConfigured"]
    return fields


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
    conversation_store: ConversationStore | None = None,
    provider_choice_store: ProviderChoiceStore | None = None,
    analysis_worker: SqlAnalysisWorker | None = None,
) -> FastAPI:
    """Build the application. Kept a factory so tests construct their own.

    Default stores are in-memory for hermetic API tests. The module-level
    ``app`` used by uvicorn/Docker is built with ``create_production_app``.
    """
    upload_limits = limits or LimitSettings()
    _configure_process_logging(force=False)
    app = FastAPI(
        title="Career Intelligence Assistant",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=_lifespan,
    )
    # Last added runs first for requests. Logging is innermost so correlation
    # and workspace are already on request.state.
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(WorkspaceCookieMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        UploadSizeLimitMiddleware, max_upload_bytes=upload_limits.max_upload_bytes
    )
    install_exception_handlers(app)
    app.state.readiness = readiness
    app.state.limits = upload_limits
    # Hermetic API tests must not inherit a hosted env default.
    app.state.providers = providers or ProviderSettings(
        completion_provider="hermetic",
        embedding_provider="hermetic",
    )
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
    resolved_conversation = (
        conversation_store
        if conversation_store is not None
        else InMemoryConversationStore()
    )
    app.state.conversation_store = resolved_conversation
    app.state.provider_choice_store = (
        provider_choice_store
        if provider_choice_store is not None
        else InMemoryProviderChoiceStore()
    )
    app.state.analysis_worker = analysis_worker
    if isinstance(resolved_conversation, SqlConversationStore):
        app.state.call_accountant = SqlCallAccountant(
            resolved_conversation._uow_factory
        )
    else:
        app.state.call_accountant = CallAccountant()
    if isinstance(app.state.role_store, InMemoryRoleStore):
        app.state.role_store.extractor_factory = _extractor_factory(app)
    app.include_router(router)
    app.include_router(providers_router, prefix="/api")
    app.include_router(cv_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(spans_router, prefix="/api")
    app.include_router(roles_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api")
    app.include_router(messages_router, prefix="/api")
    return app


def _extractor_factory(app: FastAPI) -> ExtractorFactory:
    def factory(
        workspace_id: str,
    ) -> tuple[RequirementExtractionPort, ClaimExtractionPort]:
        settings = app.state.providers or ProviderSettings()
        choice = app.state.provider_choice_store.get(
            workspace_id
        ) or default_provider_choice(settings)
        return extractors_for_choice(
            settings,
            choice,
            transport=getattr(app.state, "http_transport", None),
        )

    return factory


def create_production_app(
    *,
    readiness: ReadinessProbe | None = None,
    limits: LimitSettings | None = None,
    providers: ProviderSettings | None = None,
) -> FastAPI:
    """Wire SQL stores for the process entrypoint (uvicorn / Docker CMD)."""
    resolved_providers = providers or ProviderSettings()
    (
        cv_store,
        role_store,
        supporting_store,
        conversation_store,
        provider_choice_store,
        analysis_worker,
    ) = build_sql_stores(providers=resolved_providers)
    return create_app(
        readiness=readiness if readiness is not None else SettingsReadiness(),
        limits=limits,
        providers=resolved_providers,
        cv_store=cv_store,
        role_store=role_store,
        supporting_store=supporting_store,
        conversation_store=conversation_store,
        provider_choice_store=provider_choice_store,
        analysis_worker=analysis_worker,
    )


app = create_production_app()
