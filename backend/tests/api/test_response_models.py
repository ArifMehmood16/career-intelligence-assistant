"""Phase 11.1 — every API response model is explicit and camelCase on the wire."""

from __future__ import annotations

from fastapi.routing import APIRoute
from pydantic import BaseModel

from career_assistant.main import create_app


def test_api_model_serialises_snake_case_fields_as_camel_case() -> None:
    """Contract: Python snake_case → wire camelCase via a shared alias generator."""
    from career_assistant.api.schemas import ApiModel

    class SampleDocument(ApiModel):
        page_count: int
        parsed_at: str
        left_machine: bool

    payload = SampleDocument(
        page_count=2, parsed_at="2026-09-18T12:00:00Z", left_machine=False
    )
    assert payload.model_dump(by_alias=True) == {
        "pageCount": 2,
        "parsedAt": "2026-09-18T12:00:00Z",
        "leftMachine": False,
    }


def test_api_model_accepts_camel_case_and_snake_case_input() -> None:
    from career_assistant.api.schemas import ApiModel

    class SampleDocument(ApiModel):
        page_count: int

    from_alias = SampleDocument.model_validate({"pageCount": 3})
    from_name = SampleDocument.model_validate({"page_count": 4})
    assert from_alias.page_count == 3
    assert from_name.page_count == 4


def test_every_route_declares_an_explicit_response_model() -> None:
    app = create_app()
    api_routes = [route for route in app.routes if isinstance(route, APIRoute)]
    assert api_routes, "expected at least one API route"

    for route in api_routes:
        assert route.response_model is not None, (
            f"{route.methods} {route.path} must declare response_model"
        )
        assert route.response_model is not dict, (
            f"{route.methods} {route.path} must not use bare dict"
        )
        assert issubclass(route.response_model, BaseModel), (
            f"{route.methods} {route.path} response_model must be a Pydantic model"
        )


def test_health_response_inherits_shared_api_model() -> None:
    from career_assistant.api.schemas import ApiModel
    from career_assistant.main import HealthResponse

    assert issubclass(HealthResponse, ApiModel)
