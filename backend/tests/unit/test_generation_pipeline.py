"""Phase 10.2/10.4/10.6 — generation pipeline, hermetic bullets, cover letter refuse."""

from __future__ import annotations

from career_assistant.application.generation.pipeline import (
    GenerationCounters,
    generate_draft,
)
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)
from career_assistant.domain.claims import Claim
from career_assistant.domain.generation import (
    CoverLetterRefusal,
    draft_cover_letter,
    draft_cv_bullet_template,
)
from career_assistant.domain.groundedness import GroundednessVerdict
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.requirements import Requirement


def _req(id: str, text: str, *, must_have: bool = True) -> Requirement:
    return Requirement(
        id=id,
        text=text,
        competency=id,
        seniority_signal=None,
        must_have=must_have,
        source_span_id=f"jd-{id}",
        extraction_confidence=0.9,
        is_vague=False,
    )


def _claim(id: str, competency: str, context: str) -> Claim:
    return Claim(
        id=id,
        competency=competency,
        context=context,
        duration_signal="2y",
        recency_signal="recent",
        source_span_ids=(f"cv-{id}",),
        extraction_confidence=0.9,
    )


class _FabricatingCompletion:
    """Returns a draft that invents Kubernetes — should fail groundedness."""

    calls = 0

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="hermetic",
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=False,
            context_window_tokens=2048,
            max_output_tokens=256,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self.calls += 1
        return CompletionResult(
            text="Shipped Kubernetes operators for dbt on Snowflake.",
            provider_id="hermetic",
            model_tag="fake-v1",
            left_machine=False,
        )


class _FaithfulCompletion:
    calls = 0

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="hermetic",
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=False,
            context_window_tokens=2048,
            max_output_tokens=256,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self.calls += 1
        return CompletionResult(
            text="Owned dbt models in production on Snowflake.",
            provider_id="hermetic",
            model_tag="fake-v1",
            left_machine=False,
        )


def test_pipeline_falls_back_to_template_after_two_groundedness_failures() -> None:
    completion = _FabricatingCompletion()
    counters = GenerationCounters()
    claim = _claim("c1", "dbt", "Owned dbt models in production on Snowflake.")
    template = draft_cv_bullet_template(claim)
    result = generate_draft(
        completion=completion,
        system="Phrase only.",
        user="Rewrite the claim as a CV bullet.",
        cited_span_texts=(claim.context,),
        template_text=template,
        counters=counters,
        provider_id="hermetic",
    )
    assert completion.calls == 2
    assert result.text == template
    assert result.provenance.used_template_fallback is True
    assert result.provenance.groundedness is GroundednessVerdict.PASS
    assert counters.validator_failures == 2
    assert counters.regenerations == 1
    assert counters.template_fallbacks == 1


def test_pipeline_accepts_grounded_model_draft() -> None:
    completion = _FaithfulCompletion()
    counters = GenerationCounters()
    claim = _claim("c1", "dbt", "Owned dbt models in production on Snowflake.")
    result = generate_draft(
        completion=completion,
        system="Phrase only.",
        user="Rewrite.",
        cited_span_texts=(claim.context,),
        template_text=draft_cv_bullet_template(claim),
        counters=counters,
        provider_id="hermetic",
    )
    assert completion.calls == 1
    assert "Kubernetes" not in result.text
    assert result.provenance.used_template_fallback is False
    assert result.provenance.groundedness is GroundednessVerdict.PASS
    assert counters.template_fallbacks == 0


def test_hermetic_bullet_uses_claim_text_and_span_ids() -> None:
    claim = _claim("c1", "dbt", "Owned dbt models in production on Snowflake.")
    bullet = draft_cv_bullet_template(claim)
    assert "Owned dbt models" in bullet
    assert bullet.startswith("- ") or bullet.startswith("• ")


def test_cover_letter_refuses_below_two_met_must_haves() -> None:
    requirements = (
        _req("dbt", "dbt"),
        _req("cuda", "CUDA"),
        _req("sql", "SQL"),
    )
    mappings = (
        RequirementMapping(
            requirement_id="dbt",
            status=MappingStatus.MET,
            reason_code=MappingReason.MATCHED,
            justifying_span_ids=("cv-c1",),
            justifying_claim_ids=("c1",),
        ),
        RequirementMapping(
            requirement_id="cuda",
            status=MappingStatus.MISSING,
            reason_code=MappingReason.NO_RELATED_CLAIM,
            justifying_span_ids=(),
            justifying_claim_ids=(),
        ),
        RequirementMapping(
            requirement_id="sql",
            status=MappingStatus.MISSING,
            reason_code=MappingReason.NO_RELATED_CLAIM,
            justifying_span_ids=(),
            justifying_claim_ids=(),
        ),
    )
    claims = (_claim("c1", "dbt", "Owned dbt models in production."),)
    outcome = draft_cover_letter(
        role_title="Analytics Engineer",
        company="Acme",
        requirements=requirements,
        mappings=mappings,
        claims=claims,
    )
    assert isinstance(outcome, CoverLetterRefusal)
    assert outcome.code == "insufficient_matched_requirements"


def test_cover_letter_builds_when_two_must_haves_met() -> None:
    requirements = (
        _req("dbt", "dbt"),
        _req("sql", "SQL"),
    )
    mappings = (
        RequirementMapping(
            requirement_id="dbt",
            status=MappingStatus.MET,
            reason_code=MappingReason.MATCHED,
            justifying_span_ids=("cv-c1",),
            justifying_claim_ids=("c1",),
        ),
        RequirementMapping(
            requirement_id="sql",
            status=MappingStatus.MET,
            reason_code=MappingReason.MATCHED,
            justifying_span_ids=("cv-c2",),
            justifying_claim_ids=("c2",),
        ),
    )
    claims = (
        _claim("c1", "dbt", "Owned dbt models in production."),
        _claim("c2", "sql", "Wrote SQL for finance packs."),
    )
    outcome = draft_cover_letter(
        role_title="Analytics Engineer",
        company="Acme",
        requirements=requirements,
        mappings=mappings,
        claims=claims,
    )
    assert not isinstance(outcome, CoverLetterRefusal)
    assert "Acme" in outcome.body
    assert "dbt" in outcome.body.lower()
    assert "sql" in outcome.body.lower()
    assert set(outcome.cited_span_ids) >= {"cv-c1", "cv-c2"}


def test_adjacent_claim_does_not_support_a_cv_bullet() -> None:
    from career_assistant.domain.generation import mapping_supports_cv_bullet

    adjacent = RequirementMapping(
        requirement_id="airflow",
        status=MappingStatus.PARTIAL,
        reason_code=MappingReason.ADJACENT_CLAIM_ONLY,
        justifying_span_ids=("cv-c1",),
        justifying_claim_ids=("c1",),
    )
    matched = RequirementMapping(
        requirement_id="dbt",
        status=MappingStatus.MET,
        reason_code=MappingReason.MATCHED,
        justifying_span_ids=("cv-c2",),
        justifying_claim_ids=("c2",),
    )
    assert mapping_supports_cv_bullet(adjacent) is False
    assert mapping_supports_cv_bullet(matched) is True


def test_cover_letter_does_not_treat_adjacent_as_met() -> None:
    requirements = (
        _req("dbt", "dbt"),
        _req("airflow", "Airflow"),
    )
    mappings = (
        RequirementMapping(
            requirement_id="dbt",
            status=MappingStatus.MET,
            reason_code=MappingReason.MATCHED,
            justifying_span_ids=("cv-c1",),
            justifying_claim_ids=("c1",),
        ),
        RequirementMapping(
            requirement_id="airflow",
            status=MappingStatus.PARTIAL,
            reason_code=MappingReason.ADJACENT_CLAIM_ONLY,
            justifying_span_ids=("cv-c2",),
            justifying_claim_ids=("c2",),
        ),
    )
    claims = (
        _claim("c1", "dbt", "Owned dbt models in production."),
        _claim("c2", "python", "Worked near Airflow DAGs."),
    )
    outcome = draft_cover_letter(
        role_title="Analytics Engineer",
        company="Acme",
        requirements=requirements,
        mappings=mappings,
        claims=claims,
    )
    assert isinstance(outcome, CoverLetterRefusal)


def test_interview_pack_does_not_lead_with_adjacent_evidence() -> None:
    from career_assistant.domain.generation import build_interview_pack

    requirements = (_req("airflow", "Airflow"),)
    mappings = (
        RequirementMapping(
            requirement_id="airflow",
            status=MappingStatus.PARTIAL,
            reason_code=MappingReason.ADJACENT_CLAIM_ONLY,
            justifying_span_ids=("cv-c1",),
            justifying_claim_ids=("c1",),
        ),
    )
    pack = build_interview_pack(requirements, mappings, ())
    assert pack.lead_with == ()
    assert pack.thin_areas
