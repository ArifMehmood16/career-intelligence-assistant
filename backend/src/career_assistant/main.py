"""HTTP application factory for the Career Intelligence Assistant API.

Routes live under ``/api`` so the web tier can proxy a single prefix and the
browser never holds an API origin. See docs/api-contract.md.
"""

from typing import Literal

from fastapi import APIRouter, FastAPI

from career_assistant.api.schemas import ApiModel

router = APIRouter(prefix="/api")


class HealthResponse(ApiModel):
    """Liveness only. It answers with no database and no provider configured."""

    status: Literal["ok"]


@router.get("/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


def create_app() -> FastAPI:
    """Build the application. Kept a factory so tests construct their own."""
    app = FastAPI(
        title="Career Intelligence Assistant",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.include_router(router)
    return app


app = create_app()
