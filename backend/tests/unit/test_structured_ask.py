"""Phase 9 — structured answers from stored mappings (no vector search)."""

from __future__ import annotations

from career_assistant.domain.ask import (
    AnswerKind,
    RoleAnalysisView,
    answer_structured,
    validate_citations,
)
from career_assistant.domain.intents import Intent
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import ScoreComponent, ScoreExplanation


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


def _mapping(
    req_id: str,
    status: MappingStatus,
    reason: MappingReason,
    spans: tuple[str, ...] = (),
) -> RequirementMapping:
    return RequirementMapping(
        requirement_id=req_id,
        status=status,
        reason_code=reason,
        justifying_span_ids=spans,
        justifying_claim_ids=(),
    )


def _view(
    *,
    role_id: str = "role-1",
    title: str = "Analytics Engineer",
    score: float = 70.0,
    band: str = "partial",
    requirements: tuple[Requirement, ...] | None = None,
    mappings: tuple[RequirementMapping, ...] | None = None,
    span_text: dict[str, str] | None = None,
) -> RoleAnalysisView:
    reqs = requirements or (
        _req("dbt", "Production dbt experience"),
        _req("cuda", "CUDA experience"),
    )
    maps = mappings or (
        _mapping(
            "dbt",
            MappingStatus.MET,
            MappingReason.MATCHED,
            ("cv-dbt",),
        ),
        _mapping(
            "cuda",
            MappingStatus.MISSING,
            MappingReason.NO_RELATED_CLAIM,
        ),
    )
    explanation = ScoreExplanation(
        score=score,
        band=band,
        components=tuple(
            ScoreComponent(
                requirement_id=m.requirement_id,
                must_have=True,
                status=m.status,
                weight=3.0,
                status_factor=1.0 if m.status is MappingStatus.MET else 0.0,
                recency_factor=1.0,
                contribution=3.0 if m.status is MappingStatus.MET else 0.0,
            )
            for m in maps
        ),
        denominator=6.0,
        numerator=score / 100.0 * 6.0,
    )
    return RoleAnalysisView(
        role_id=role_id,
        title=title,
        explanation=explanation,
        requirements=reqs,
        mappings=maps,
        span_texts=span_text
        or {
            "cv-dbt": "Owned dbt models in production.",
            "jd-dbt": "Production dbt experience",
            "jd-cuda": "CUDA experience",
        },
    )


def test_gaps_intent_answers_from_mapping_without_vector_search() -> None:
    result = answer_structured(
        Intent.GAPS,
        "What skills am I missing for this role?",
        roles=(_view(),),
        known_span_ids=frozenset({"cv-dbt", "jd-dbt", "jd-cuda"}),
    )
    assert result.kind is AnswerKind.ANSWER
    assert "CUDA" in result.content or "cuda" in result.content.lower()
    assert "dbt" not in result.content.lower() or "missing" in result.content.lower()
    # Missing gaps have no CV citation; answer may cite JD requirement spans only.
    assert all(c.span_id in {"jd-cuda", "jd-dbt", "cv-dbt"} for c in result.citations)


def test_fit_intent_reports_stored_score_and_band() -> None:
    result = answer_structured(
        Intent.FIT,
        "How well do I fit this role?",
        roles=(_view(score=70.0, band="partial"),),
        known_span_ids=frozenset({"cv-dbt", "jd-dbt", "jd-cuda"}),
    )
    assert result.kind is AnswerKind.ANSWER
    assert "70" in result.content
    assert "partial" in result.content.lower()


def test_evidence_intent_cites_justifying_spans() -> None:
    result = answer_structured(
        Intent.EVIDENCE_FOR_REQUIREMENT,
        "What evidence do I have for the dbt requirement?",
        roles=(_view(),),
        known_span_ids=frozenset({"cv-dbt", "jd-dbt", "jd-cuda"}),
    )
    assert result.kind is AnswerKind.ANSWER
    assert any(c.span_id == "cv-dbt" for c in result.citations)


def test_evidence_for_missing_requirement_is_insufficient() -> None:
    result = answer_structured(
        Intent.EVIDENCE_FOR_REQUIREMENT,
        "What evidence do I have for the cuda requirement?",
        roles=(_view(),),
        known_span_ids=frozenset({"cv-dbt", "jd-dbt", "jd-cuda"}),
    )
    assert result.kind is AnswerKind.INSUFFICIENT
    assert result.citations == ()


def test_compare_roles_ranks_by_stored_scores() -> None:
    weaker = _view(role_id="role-a", title="A", score=40.0, band="limited")
    stronger = _view(role_id="role-b", title="B", score=85.0, band="strong")
    result = answer_structured(
        Intent.COMPARE_ROLES,
        "Which role is a stronger match?",
        roles=(weaker, stronger),
        known_span_ids=frozenset({"cv-dbt", "jd-dbt", "jd-cuda"}),
    )
    assert result.kind is AnswerKind.ANSWER
    # Stronger role named before weaker in the ranking sentence.
    assert result.content.index("B") < result.content.index("A")
    assert "CUDA" in result.content or "cuda" in result.content.lower()


def test_interview_prep_lists_must_haves_by_status() -> None:
    result = answer_structured(
        Intent.INTERVIEW_PREPARATION,
        "Help me prepare for the interview",
        roles=(_view(),),
        known_span_ids=frozenset({"cv-dbt", "jd-dbt", "jd-cuda"}),
    )
    assert result.kind is AnswerKind.ANSWER
    assert "dbt" in result.content.lower()
    assert "cuda" in result.content.lower()


def test_unresolvable_citation_reduces_to_insufficient() -> None:
    view = _view(
        mappings=(
            _mapping(
                "dbt",
                MappingStatus.MET,
                MappingReason.MATCHED,
                ("ghost-span",),
            ),
        ),
        requirements=(_req("dbt", "Production dbt experience"),),
        span_text={"jd-dbt": "Production dbt experience"},
    )
    result = answer_structured(
        Intent.EVIDENCE_FOR_REQUIREMENT,
        "What evidence do I have for the dbt requirement?",
        roles=(view,),
        known_span_ids=frozenset({"jd-dbt"}),  # ghost-span absent
    )
    assert result.kind is AnswerKind.INSUFFICIENT
    assert result.citations == ()


def test_validate_citations_drops_unknown_spans() -> None:
    from career_assistant.domain.ask import AnswerCitation, AnswerResult

    raw = AnswerResult(
        kind=AnswerKind.ANSWER,
        content="Owned dbt.",
        citations=(AnswerCitation(span_id="ghost", label="x"),),
        intent=Intent.EVIDENCE_FOR_REQUIREMENT,
    )
    validated = validate_citations(raw, known_span_ids=frozenset({"cv-dbt"}))
    assert validated.kind is AnswerKind.INSUFFICIENT
    assert validated.citations == ()
