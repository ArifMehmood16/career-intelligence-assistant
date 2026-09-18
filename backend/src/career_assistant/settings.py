"""Provider configuration loaded at construction — never logged or returned."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
