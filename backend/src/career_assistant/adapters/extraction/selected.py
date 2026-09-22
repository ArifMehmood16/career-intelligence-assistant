"""Build requirement and claim extractors from a workspace completion choice."""

from __future__ import annotations

from career_assistant.adapters.extraction.claims_model import ModelClaimExtractor
from career_assistant.adapters.extraction.claims_rules import RulesClaimExtractor
from career_assistant.adapters.extraction.model_backed import ModelRequirementExtractor
from career_assistant.adapters.extraction.rules import RulesRequirementExtractor
from career_assistant.adapters.providers.factory import build_completion_port
from career_assistant.adapters.providers.http_transport import HttpTransport
from career_assistant.adapters.relatedness.model import ModelAdjudicator
from career_assistant.adapters.relatedness.null import NullAdjudicator
from career_assistant.application.ports.adjudication import AdjudicationPort
from career_assistant.application.ports.extraction import (
    ClaimExtractionPort,
    RequirementExtractionPort,
)
from career_assistant.application.providers.accounting import (
    AccountingCompletion,
    CallAccountant,
)
from career_assistant.application.providers.catalogue import ProviderChoice
from career_assistant.domain.assessment import AssessmentBatchBudget
from career_assistant.settings import ProviderSettings


def extractors_for_choice(
    settings: ProviderSettings,
    choice: ProviderChoice,
    *,
    transport: HttpTransport | None = None,
    accountant: CallAccountant | None = None,
    workspace_id: str | None = None,
) -> tuple[RequirementExtractionPort, ClaimExtractionPort]:
    requirement, claim, _adjudicator = analysis_ports_for_choice(
        settings,
        choice,
        transport=transport,
        accountant=accountant,
        workspace_id=workspace_id,
    )
    return requirement, claim


def adjudicator_for_choice(
    settings: ProviderSettings,
    choice: ProviderChoice,
    *,
    transport: HttpTransport | None = None,
    accountant: CallAccountant | None = None,
    workspace_id: str | None = None,
) -> AdjudicationPort:
    _requirement, _claim, adjudicator = analysis_ports_for_choice(
        settings,
        choice,
        transport=transport,
        accountant=accountant,
        workspace_id=workspace_id,
    )
    return adjudicator


def analysis_ports_for_choice(
    settings: ProviderSettings,
    choice: ProviderChoice,
    *,
    transport: HttpTransport | None = None,
    accountant: CallAccountant | None = None,
    workspace_id: str | None = None,
) -> tuple[RequirementExtractionPort, ClaimExtractionPort, AdjudicationPort]:
    if choice.answer_provider_id == "hermetic":
        return (
            RulesRequirementExtractor(),
            RulesClaimExtractor(),
            NullAdjudicator(),
        )
    completion = build_completion_port(
        settings,
        transport=transport,
        provider_id=choice.answer_provider_id,
        model_tag=choice.answer_model,
    )
    req_port = completion
    claim_port = completion
    assess_port = completion
    if accountant is not None and workspace_id:
        req_port = AccountingCompletion(
            completion,
            accountant,
            workspace_id=workspace_id,
            purpose="extract_requirements",
        )
        claim_port = AccountingCompletion(
            completion,
            accountant,
            workspace_id=workspace_id,
            purpose="extract_claims",
        )
        assess_port = AccountingCompletion(
            completion,
            accountant,
            workspace_id=workspace_id,
            purpose="assess",
        )
    return (
        ModelRequirementExtractor(req_port),
        ModelClaimExtractor(
            claim_port, batch_size=settings.claim_batch_max_spans
        ),
        ModelAdjudicator(
            assess_port,
            budget=AssessmentBatchBudget(
                max_requirements=settings.assessment_batch_max_requirements,
                output_tokens_per_requirement=(
                    settings.assessment_output_tokens_per_requirement
                ),
                max_output_tokens=settings.llm_max_output_tokens,
            ),
        ),
    )
