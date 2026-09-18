"""Generation pipeline: phrase → validate → regenerate once → template fallback."""

from __future__ import annotations

from dataclasses import dataclass

from career_assistant.application.ports.completion import CompletionPort
from career_assistant.application.ports.types import CompletionRequest
from career_assistant.domain.groundedness import (
    GroundednessVerdict,
    validate_groundedness,
)


@dataclass
class GenerationCounters:
    validator_failures: int = 0
    regenerations: int = 0
    template_fallbacks: int = 0


@dataclass(frozen=True, slots=True)
class DraftProvenance:
    provider_id: str
    model_tag: str
    left_machine: bool
    groundedness: GroundednessVerdict
    used_template_fallback: bool
    regeneration_count: int


@dataclass(frozen=True, slots=True)
class GeneratedDraft:
    text: str
    provenance: DraftProvenance


def generate_draft(
    *,
    completion: CompletionPort,
    system: str,
    user: str,
    cited_span_texts: tuple[str, ...] | list[str],
    template_text: str,
    counters: GenerationCounters,
    provider_id: str,
    max_output_tokens: int = 256,
) -> GeneratedDraft:
    """Phrase through the completion port with groundedness enforced."""
    regenerations = 0
    last_model = "unknown"
    left_machine = False

    for attempt in range(2):
        result = completion.complete(
            CompletionRequest(
                system=system,
                user=user,
                max_output_tokens=max_output_tokens,
            )
        )
        last_model = result.model_tag
        left_machine = result.left_machine
        check = validate_groundedness(result.text, cited_span_texts)
        if check.verdict is GroundednessVerdict.PASS:
            return GeneratedDraft(
                text=result.text,
                provenance=DraftProvenance(
                    provider_id=result.provider_id or provider_id,
                    model_tag=result.model_tag,
                    left_machine=result.left_machine,
                    groundedness=GroundednessVerdict.PASS,
                    used_template_fallback=False,
                    regeneration_count=regenerations,
                ),
            )
        counters.validator_failures += 1
        if attempt == 0:
            regenerations += 1
            counters.regenerations += 1

    # Template path is span-backed by construction; still run the validator.
    check = validate_groundedness(template_text, cited_span_texts)
    counters.template_fallbacks += 1
    return GeneratedDraft(
        text=template_text,
        provenance=DraftProvenance(
            provider_id=provider_id,
            model_tag=last_model,
            left_machine=left_machine,
            groundedness=check.verdict,
            used_template_fallback=True,
            regeneration_count=regenerations,
        ),
    )
