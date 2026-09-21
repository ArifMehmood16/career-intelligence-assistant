"""Build requirement and claim extractors from a workspace completion choice."""

from __future__ import annotations

from career_assistant.adapters.extraction.claims_model import ModelClaimExtractor
from career_assistant.adapters.extraction.claims_rules import RulesClaimExtractor
from career_assistant.adapters.extraction.model_backed import ModelRequirementExtractor
from career_assistant.adapters.extraction.rules import RulesRequirementExtractor
from career_assistant.adapters.providers.factory import build_completion_port
from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.application.ports.extraction import (
    ClaimExtractionPort,
    RequirementExtractionPort,
)
from career_assistant.application.providers.catalogue import ProviderChoice
from career_assistant.settings import ProviderSettings


def extractors_for_choice(
    settings: ProviderSettings,
    choice: ProviderChoice,
    *,
    transport: HttpTransport | None = None,
) -> tuple[RequirementExtractionPort, ClaimExtractionPort]:
    if choice.answer_provider_id == "hermetic":
        return RulesRequirementExtractor(), RulesClaimExtractor()
    completion = build_completion_port(
        settings,
        transport=transport,
        provider_id=choice.answer_provider_id,
        model_tag=choice.answer_model,
    )
    return ModelRequirementExtractor(completion), ModelClaimExtractor(completion)
