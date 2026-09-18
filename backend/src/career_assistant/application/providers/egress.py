"""Egress gate: hosted adapters are constructible only when permitted."""

from __future__ import annotations

from dataclasses import dataclass

from career_assistant.application.ports.errors import EgressNotPermittedError


@dataclass(frozen=True, slots=True)
class HostedEgressPolicy:
    """Single chokepoint for whether content may leave the machine."""

    allow_hosted: bool
    openai_api_key: str | None
    anthropic_api_key: str | None

    def assert_openai_constructible(self) -> str:
        return self._require_hosted_key("openai", self.openai_api_key)

    def assert_anthropic_constructible(self) -> str:
        return self._require_hosted_key("anthropic", self.anthropic_api_key)

    def openai_available(self) -> bool:
        return self.allow_hosted and bool(self.openai_api_key)

    def anthropic_available(self) -> bool:
        return self.allow_hosted and bool(self.anthropic_api_key)

    def _require_hosted_key(self, provider_id: str, key: str | None) -> str:
        if not self.allow_hosted or not key:
            raise EgressNotPermittedError(
                f"hosted provider {provider_id!r} is not permitted: "
                "ALLOW_HOSTED_PROVIDERS must be true and the provider key present"
            )
        return key
