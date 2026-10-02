"""Construction inputs shared by the registered provider builders."""

from __future__ import annotations

from dataclasses import dataclass

from career_assistant.adapters.providers.call_gate import (
    HostedCallGate,
    shared_hosted_call_gate,
)
from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.providers.resilience import ResiliencePolicy
from career_assistant.application.providers.egress import HostedEgressPolicy
from career_assistant.application.providers.model_catalogue import ModelCatalogue
from career_assistant.settings import ProviderSettings


@dataclass(frozen=True, slots=True)
class ProviderConstruction:
    settings: ProviderSettings
    egress: HostedEgressPolicy
    transport: HttpTransport
    resilience: ResiliencePolicy
    model_tag: str | None
    catalogue: ModelCatalogue

    def hosted_gate(self) -> HostedCallGate:
        return shared_hosted_call_gate(self.settings.hosted_max_in_flight)
