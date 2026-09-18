"""HTTP wire models — camelCase on the wire, snake_case in Python."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Shared base for every request/response schema exposed under ``/api``."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        serialize_by_alias=True,
    )


class ErrorBody(ApiModel):
    code: str
    message: str
    correlation_id: str


class ErrorEnvelope(ApiModel):
    error: ErrorBody


class ReadyResponse(ApiModel):
    database: str
    migrations: str
    completion_provider: str
    embedding_provider: str
    hosted_egress: bool
