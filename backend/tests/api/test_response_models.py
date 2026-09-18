"""Phase 11.1 — every API response model is explicit and camelCase on the wire."""

from __future__ import annotations

from collections.abc import Iterator
from typing import get_args, get_origin

from fastapi.responses import PlainTextResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel
from starlette.routing import BaseRoute

from career_assistant.main import create_app


def _iter_api_routes(routes: list[BaseRoute]) -> Iterator[APIRoute]:
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif hasattr(route, "routes"):
            yield from _iter_api_routes(list(route.routes))
        elif hasattr(route, "original_router"):
            yield from _iter_api_routes(list(route.original_router.routes))


def _is_plain_text_route(route: APIRoute) -> bool:
    response_class = route.response_class
    return isinstance(response_class, type) and issubclass(
        response_class, PlainTextResponse
    )


def _assert_response_model(model: object, *, route: APIRoute) -> None:
    # 204 No Content routes may omit a body model.
    # Markdown export routes use PlainTextResponse deliberately (not JSON).
    if model is None:
        assert (
            route.status_code == 204
            or 204 in (route.status_code or (),)
            or _is_plain_text_route(route)
        ), f"{route.methods} {route.path} needs an explicit response_model"
        return
    assert model is not dict, f"{route.methods} {route.path} must not use bare dict"
    origin = get_origin(model)
    if origin is list:
        args = get_args(model)
        assert args, (
            f"{route.methods} {route.path} list response_model needs an item type"
        )
        assert issubclass(args[0], BaseModel), (
            f"{route.methods} {route.path} list item must be a Pydantic model"
        )
        return
    if origin is not None:
        args = [arg for arg in get_args(model) if arg is not type(None)]
        assert args, f"{route.methods} {route.path} union response_model is empty"
        assert issubclass(args[0], BaseModel), (
            f"{route.methods} {route.path} union item must be a Pydantic model"
        )
        return
    assert isinstance(model, type) and issubclass(model, BaseModel), (
        f"{route.methods} {route.path} response_model must be a Pydantic model"
    )


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
    api_routes = list(_iter_api_routes(list(app.routes)))
    assert api_routes, "expected at least one API route"

    for route in api_routes:
        _assert_response_model(route.response_model, route=route)


def test_health_response_inherits_shared_api_model() -> None:
    from career_assistant.api.schemas import ApiModel
    from career_assistant.main import HealthResponse

    assert issubclass(HealthResponse, ApiModel)
