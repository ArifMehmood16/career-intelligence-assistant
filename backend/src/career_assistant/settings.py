"""Provider and database configuration loaded at construction — never logged."""

from __future__ import annotations

from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PSYCOPG_SCHEME = "postgresql+psycopg"


class DatabaseSettings(BaseSettings):
    """PostgreSQL topology contract — no SQLite or in-memory production path."""

    model_config = SettingsConfigDict(
        env_file=("config/app.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://career:career@localhost:5432/career_assistant"
    )
    test_database_url: str = (
        "postgresql+psycopg://career:career@localhost:5432/career_assistant_test"
    )

    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=5, ge=0)
    db_pool_timeout_seconds: float = Field(default=30.0, gt=0)
    db_pool_pre_ping: bool = True
    db_statement_timeout_ms: int = Field(default=30_000, ge=1)
    db_lock_timeout_ms: int = Field(default=5_000, ge=1)
    db_echo: bool = False
    embedding_vector_dimensions: int = Field(default=64, ge=1)

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _require_psycopg(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != _PSYCOPG_SCHEME:
            raise ValueError(
                f"database URLs must use {_PSYCOPG_SCHEME}:// — "
                "SQLite and other drivers are not a production path"
            )
        if not parsed.hostname:
            raise ValueError("database URL must include a hostname")
        return value

    @model_validator(mode="after")
    def _test_url_must_differ(self) -> DatabaseSettings:
        if self.test_database_url == self.database_url:
            raise ValueError(
                "TEST_DATABASE_URL must name a separate database from DATABASE_URL"
            )
        return self

    def host_path_hostname(self) -> str:
        host = urlparse(self.database_url).hostname
        assert host is not None
        return host

    def host_path_port(self) -> int:
        parsed = urlparse(self.database_url)
        if parsed.port is not None:
            return parsed.port
        return 5432

    def is_compose_topology(self) -> bool:
        return self.host_path_hostname() == "db" and self.host_path_port() == 5432


class ProviderSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("config/app.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    completion_provider: str = "hermetic"
    embedding_provider: str = "hermetic"
    allow_hosted_providers: bool = False

    ollama_base_url: str = "http://localhost:11434"
    ollama_completion_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"

    openai_api_key: SecretStr | None = None
    openai_completion_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    anthropic_api_key: SecretStr | None = None
    anthropic_completion_model: str = "claude-sonnet-4-0"

    provider_timeout_seconds: float = 60.0
    provider_max_retries: int = 2
    provider_breaker_failure_threshold: int = 5
    provider_allow_local_fallback: bool = False
    track_token_usage: bool = True

    llm_max_output_tokens: int = Field(default=1024, ge=1)

    def secret_values(self) -> tuple[str, ...]:
        """Configured secrets for redaction tests — never expose via routes."""
        values: list[str] = []
        if self.openai_api_key is not None:
            raw = self.openai_api_key.get_secret_value()
            if raw:
                values.append(raw)
        if self.anthropic_api_key is not None:
            raw = self.anthropic_api_key.get_secret_value()
            if raw:
                values.append(raw)
        return tuple(values)

    def public_snapshot(self) -> dict[str, object]:
        """Safe view for diagnostics — no keys, including masked forms."""
        return {
            "completionProvider": self.completion_provider,
            "embeddingProvider": self.embedding_provider,
            "allowHostedProviders": self.allow_hosted_providers,
            "openaiKeyConfigured": bool(
                self.openai_api_key and self.openai_api_key.get_secret_value()
            ),
            "anthropicKeyConfigured": bool(
                self.anthropic_api_key and self.anthropic_api_key.get_secret_value()
            ),
            "ollamaBaseUrl": self.ollama_base_url,
            "providerAllowLocalFallback": self.provider_allow_local_fallback,
        }


class LimitSettings(BaseSettings):
    """Upload and request caps — enforced at the HTTP boundary before buffering."""

    model_config = SettingsConfigDict(
        env_file=("config/app.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_upload_bytes: int = Field(default=10_485_760, ge=1)
    max_document_pages: int = Field(default=40, ge=1)
    max_document_chars: int = Field(default=400_000, ge=1)
    max_question_chars: int = Field(default=1000, ge=1)
    max_context_chars: int = Field(default=12_000, ge=1)
    max_excerpt_chars: int = Field(default=600, ge=1)
    max_roles_per_workspace: int = Field(default=25, ge=1)
