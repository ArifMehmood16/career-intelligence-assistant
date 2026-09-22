"""Phase 7 — mapping policy and deterministic scoring (pure domain)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from career_assistant.application.scoring.rubric_loader import load_scoring_rubric
from career_assistant.domain.claims import Claim
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
    map_requirement,
    map_requirements,
)
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import (
    counterfactual_delta,
    score_fit,
)

ROOT = Path(__file__).resolve().parents[3]
RUBRIC_PATH = ROOT / "config" / "scoring_rubric.toml"


def _req(
    *,
    id: str,
    text: str,
    competency: str,
    must_have: bool = True,
) -> Requirement:
    return Requirement(
        id=id,
        text=text,
        competency=competency,
        seniority_signal=None,
        must_have=must_have,
        source_span_id=f"span-{id}",
        extraction_confidence=0.9,
        is_vague=False,
    )


def _claim(
    *,
    id: str,
    competency: str,
    context: str,
    recency: str = "recent",
    span_ids: tuple[str, ...] | None = None,
) -> Claim:
    return Claim(
        id=id,
        competency=competency,
        context=context,
        duration_signal="2y",
        recency_signal=recency,
        source_span_ids=span_ids or (f"cspan-{id}",),
        extraction_confidence=0.9,
    )


def test_mapping_met_when_competency_and_evidence_align() -> None:
    req = _req(id="r1", text="Production dbt experience", competency="dbt")
    claim = _claim(
        id="c1",
        competency="dbt",
        context="Owned dbt models in production on Snowflake.",
    )
    result = map_requirement(req, (claim,))
    assert result.status is MappingStatus.MET
    assert "cspan-c1" in result.justifying_span_ids


def test_mapping_missing_when_no_related_claim() -> None:
    req = _req(id="r1", text="CUDA experience", competency="cuda")
    claim = _claim(id="c1", competency="dbt", context="Owned dbt models.")
    result = map_requirement(req, (claim,))
    assert result.status is MappingStatus.MISSING
    assert result.reason_code is MappingReason.NO_RELATED_CLAIM
    assert result.justifying_span_ids == ()


def test_mapping_partial_for_adjacent_competency_only() -> None:
    req = _req(id="r1", text="Production Airflow ownership", competency="airflow")
    claim = _claim(
        id="c1",
        competency="python",
        context="Collaborated with engineers who maintained Airflow DAGs.",
    )
    result = map_requirement(req, (claim,))
    assert result.status is MappingStatus.PARTIAL
    assert result.reason_code is MappingReason.ADJACENT_CLAIM_ONLY


def test_mapping_partial_when_only_old_evidence() -> None:
    req = _req(id="r1", text="Production Spark jobs", competency="spark")
    claim = _claim(
        id="c1",
        competency="spark",
        context="Built production Spark jobs on Hadoop.",
        recency="old",
    )
    result = map_requirement(req, (claim,))
    assert result.status is MappingStatus.PARTIAL
    assert result.reason_code is MappingReason.EVIDENCE_TOO_OLD


def test_high_similarity_without_overlap_or_competency_is_related_not_missing() -> None:
    req = _req(
        id="r1",
        text="Kubernetes cluster autoscaling",
        competency="kubernetes",
    )
    claim = _claim(
        id="c1",
        competency="platform",
        context="Scaled container orchestration workloads across regions.",
    )
    result = map_requirement(
        req,
        (claim,),
        similarities={("r1", "c1"): 0.9},
    )
    assert result.status is not MappingStatus.MISSING
    assert result.reason_code is MappingReason.ADJACENT_CLAIM_ONLY
    assert result.justifying_claim_ids == ("c1",)


def test_low_similarity_without_overlap_or_competency_is_missing() -> None:
    req = _req(
        id="r1",
        text="Kubernetes cluster autoscaling",
        competency="kubernetes",
    )
    claim = _claim(
        id="c1",
        competency="platform",
        context="Scaled container orchestration workloads across regions.",
    )
    result = map_requirement(
        req,
        (claim,),
        similarities={("r1", "c1"): 0.2},
    )
    assert result.status is MappingStatus.MISSING
    assert result.reason_code is MappingReason.NO_RELATED_CLAIM
    assert result.justifying_span_ids == ()


def test_similarities_are_keyed_per_requirement_claim_pair() -> None:
    req_a = _req(
        id="ra",
        text="Kubernetes cluster autoscaling",
        competency="kubernetes",
    )
    req_b = _req(
        id="rb",
        text="CUDA kernel authoring",
        competency="cuda",
    )
    claim = _claim(
        id="c1",
        competency="platform",
        context="Scaled container orchestration workloads across regions.",
    )
    mappings = map_requirements(
        (req_a, req_b),
        (claim,),
        similarities={("ra", "c1"): 0.9, ("rb", "c1"): 0.2},
    )
    by_id = {item.requirement_id: item for item in mappings}
    assert by_id["ra"].status is not MappingStatus.MISSING
    assert by_id["rb"].status is MappingStatus.MISSING


def test_supplying_similarities_never_lowers_score_and_is_deterministic() -> None:
    rubric = load_scoring_rubric(RUBRIC_PATH)
    requirements = (
        _req(
            id="r1",
            text="Kubernetes cluster autoscaling",
            competency="kubernetes",
        ),
        _req(id="r2", text="Production dbt experience", competency="dbt"),
    )
    claims = (
        _claim(
            id="c1",
            competency="platform",
            context="Scaled container orchestration workloads across regions.",
        ),
        _claim(id="c2", competency="dbt", context="Owned dbt models in production."),
    )
    without = map_requirements(requirements, claims)
    score_without = score_fit(requirements, without, claims, rubric).score
    similarities = {("r1", "c1"): 0.9, ("r2", "c2"): 0.1}
    with_sims = map_requirements(requirements, claims, similarities=similarities)
    score_with = score_fit(requirements, with_sims, claims, rubric).score
    again = map_requirements(requirements, claims, similarities=similarities)
    score_again = score_fit(requirements, again, claims, rubric).score
    assert score_with >= score_without
    assert score_with == score_again


def test_similarity_scores_can_surface_candidates_but_policy_decides() -> None:
    req = _req(id="r1", text="dbt analytics engineering", competency="dbt")
    unrelated = _claim(
        id="c1",
        competency="general",
        context="Mentored juniors on delivery practices.",
    )
    # High similarity alone must not force met without competency/content policy.
    result = map_requirement(
        req,
        (unrelated,),
        similarities={("r1", "c1"): 0.99},
    )
    assert result.status is not MappingStatus.MET


def test_score_reads_rubric_and_is_deterministic() -> None:
    rubric = load_scoring_rubric(RUBRIC_PATH)
    requirements = (
        _req(id="r1", text="dbt", competency="dbt", must_have=True),
        _req(id="r2", text="Looker", competency="bi", must_have=False),
    )
    claims = (
        _claim(id="c1", competency="dbt", context="Owned dbt models in production."),
    )
    mappings = map_requirements(requirements, claims)
    first = score_fit(requirements, mappings, claims, rubric)
    second = score_fit(requirements, mappings, claims, rubric)
    assert first.score == second.score
    assert 0 <= first.score <= 100
    assert first.band in {"strong", "partial", "limited"}
    assert first.components
    # Every component traces to requirement ids from the mapping.
    explained_ids = {item.requirement_id for item in first.components}
    assert explained_ids == {"r1", "r2"}
    assert all(item.adjudicated is False for item in first.components)


def test_adjudication_confirmed_embedding_match_is_flagged_on_the_explanation() -> None:
    """PLAN 13C.6 — met through model adjudication of a disagreement is labelled.

    Arithmetic is unchanged: the flag is additive on the explanation object.
    """
    rubric = load_scoring_rubric(RUBRIC_PATH)
    req = _req(
        id="r1",
        text="Kubernetes cluster autoscaling",
        competency="kubernetes",
    )
    claim = _claim(
        id="c1",
        competency="platform",
        context="Scaled container orchestration workloads across regions.",
    )
    mapping = map_requirement(
        req,
        (claim,),
        similarities={("r1", "c1"): 0.9},
        adjudications={("r1", "c1"): True},
    )
    assert mapping.signals.lexical is False
    assert mapping.signals.embedding is True
    assert mapping.signals.adjudication is True
    explanation = score_fit((req,), (mapping,), (claim,), rubric)
    flagged = explanation.components[0]
    assert flagged.adjudicated is True
    assert flagged.status is not MappingStatus.MISSING
    unflagged = map_requirement(
        req,
        (claim,),
        similarities={("r1", "c1"): 0.9},
    )
    same_math = score_fit((req,), (unflagged,), (claim,), rubric)
    assert flagged.contribution == same_math.components[0].contribution
    assert same_math.components[0].adjudicated is False


def test_adding_a_met_requirement_never_lowers_score() -> None:
    rubric = load_scoring_rubric(RUBRIC_PATH)
    base_reqs = (_req(id="r1", text="dbt", competency="dbt"),)
    claims = (
        _claim(id="c1", competency="dbt", context="Owned dbt models in production."),
        _claim(id="c2", competency="sql", context="Wrote SQL for finance packs."),
    )
    base_map = map_requirements(base_reqs, claims)
    base_score = score_fit(base_reqs, base_map, claims, rubric).score

    richer_reqs = base_reqs + (_req(id="r2", text="Strong SQL", competency="sql"),)
    richer_map = map_requirements(richer_reqs, claims)
    richer_score = score_fit(richer_reqs, richer_map, claims, rubric).score
    assert richer_score >= base_score


def test_counterfactual_delta_for_closing_a_gap() -> None:
    rubric = load_scoring_rubric(RUBRIC_PATH)
    requirements = (
        _req(id="r1", text="dbt", competency="dbt"),
        _req(id="r2", text="CUDA", competency="cuda"),
    )
    claims = (
        _claim(id="c1", competency="dbt", context="Owned dbt models in production."),
    )
    mappings = map_requirements(requirements, claims)
    baseline = score_fit(requirements, mappings, claims, rubric)
    delta = counterfactual_delta(
        requirements,
        mappings,
        claims,
        rubric,
        requirement_id="r2",
    )
    assert delta > 0
    assert baseline.score + delta <= 100 + 1e-9


def test_fixture_cv_and_jd_produce_stable_score_without_model() -> None:
    from datetime import date

    from career_assistant.adapters.extraction.claims_rules import RulesClaimExtractor
    from career_assistant.adapters.extraction.rules import RulesRequirementExtractor
    from career_assistant.domain.documents import DocumentKind
    from career_assistant.domain.normalisation import normalise_text

    jd = normalise_text(
        (ROOT / "sample-data/fixtures/job-descriptions/jd-clean-match.txt").read_text(
            encoding="utf-8"
        )
    )
    cv = normalise_text(
        (ROOT / "sample-data/fixtures/resumes/cv-strong-match.txt").read_text(
            encoding="utf-8"
        )
    )
    reqs = (
        RulesRequirementExtractor()
        .extract(
            document_id="jd",
            document_kind=DocumentKind.JOB_DESCRIPTION,
            normalised_text=jd,
        )
        .requirements
    )
    claims = (
        RulesClaimExtractor(as_of=date(2026, 9, 18))
        .extract(
            document_id="cv",
            document_kind=DocumentKind.CV,
            normalised_text=cv,
        )
        .claims
    )
    rubric = load_scoring_rubric(RUBRIC_PATH)
    mappings = map_requirements(reqs, claims)
    a = score_fit(reqs, mappings, claims, rubric)
    b = score_fit(reqs, mappings, claims, rubric)
    assert a.score == b.score
    assert 0 <= a.score <= 100
    assert len(a.components) == len(reqs)


def test_no_scoreable_requirements_is_unscored_not_a_limited_match() -> None:
    rubric = load_scoring_rubric(RUBRIC_PATH)
    explanation = score_fit((), (), (), rubric)
    assert explanation.score == 0
    assert explanation.band == "unscored"
    assert explanation.components == ()


def _scored(
    requirement: Requirement,
    *,
    status: MappingStatus,
    reason: MappingReason,
    unknown_conditions: tuple[str, ...] = (),
    contradiction: bool = False,
) -> RequirementMapping:
    return RequirementMapping(
        requirement_id=requirement.id,
        status=status,
        reason_code=reason,
        justifying_span_ids=(),
        justifying_claim_ids=(),
        unknown_conditions=unknown_conditions,
        contradiction=contradiction,
    )


def test_duplicate_requirement_text_scores_once() -> None:
    """PLAN 13D.5 — the same requirement stated twice does not inflate the fit."""
    rubric = load_scoring_rubric(RUBRIC_PATH)
    sql_a = _req(id="a", text="Write production SQL", competency="sql")
    sql_b = _req(id="b", text="write   production sql", competency="sql")
    python = _req(id="c", text="Production Python", competency="python")
    scored = score_fit(
        (sql_a, sql_b, python),
        (
            _scored(sql_a, status=MappingStatus.MET, reason=MappingReason.MATCHED),
            _scored(sql_b, status=MappingStatus.MET, reason=MappingReason.MATCHED),
            _scored(
                python,
                status=MappingStatus.MISSING,
                reason=MappingReason.NO_RELATED_CLAIM,
            ),
        ),
        (),
        rubric,
    )
    assert scored.score == 50.0
    assert scored.denominator == 6.0


def test_unknown_or_conflicting_evidence_is_not_full_coverage() -> None:
    rubric = load_scoring_rubric(RUBRIC_PATH)
    requirement = _req(id="r1", text="Lead a platform team", competency="leadership")
    full = score_fit(
        (requirement,),
        (
            _scored(
                requirement, status=MappingStatus.MET, reason=MappingReason.MATCHED
            ),
        ),
        (),
        rubric,
    )
    unknown = score_fit(
        (requirement,),
        (
            _scored(
                requirement,
                status=MappingStatus.MET,
                reason=MappingReason.MATCHED,
                unknown_conditions=("team size",),
            ),
        ),
        (),
        rubric,
    )
    conflict = score_fit(
        (requirement,),
        (
            _scored(
                requirement,
                status=MappingStatus.MET,
                reason=MappingReason.MATCHED,
                contradiction=True,
            ),
        ),
        (),
        rubric,
    )
    assert full.score == 100.0
    assert unknown.score == 50.0
    assert conflict.score == 50.0


def test_incomplete_assessment_is_not_banded_as_a_poor_fit() -> None:
    rubric = load_scoring_rubric(RUBRIC_PATH)
    requirement = _req(id="r1", text="Five years leading Python", competency="python")
    poor = score_fit(
        (requirement,),
        (
            _scored(
                requirement,
                status=MappingStatus.MISSING,
                reason=MappingReason.NO_RELATED_CLAIM,
            ),
        ),
        (),
        rubric,
    )
    incomplete = score_fit(
        (requirement,),
        (
            _scored(
                requirement,
                status=MappingStatus.MISSING,
                reason=MappingReason.ASSESSMENT_INCOMPLETE,
            ),
        ),
        (),
        rubric,
    )
    assert poor.score == 0.0
    assert incomplete.score == 0.0
    assert poor.band == "limited"
    assert incomplete.band == "incomplete"


def test_introductory_course_does_not_meet_production_leadership() -> None:
    """PLAN 13D.5 — a Python course is not five years of production leadership."""
    requirement = _req(
        id="req-python-leadership",
        text="Five years leading production Python systems",
        competency="python",
    )
    requirement = Requirement(
        id=requirement.id,
        text=requirement.text,
        competency=requirement.competency,
        seniority_signal="five_years_leadership",
        must_have=True,
        source_span_id=requirement.source_span_id,
        extraction_confidence=0.9,
        is_vague=False,
    )
    course = _claim(
        id="claim-course",
        competency="python",
        context="Completed an introductory Python course.",
    )
    course = Claim(
        id=course.id,
        competency=course.competency,
        context=course.context,
        duration_signal="course",
        recency_signal="recent",
        source_span_ids=course.source_span_ids,
        extraction_confidence=0.9,
    )
    result = map_requirement(requirement, (course,))
    assert result.status is MappingStatus.MISSING
    assert result.justifying_span_ids == ()
    scored = score_fit(
        (requirement,),
        (result,),
        (course,),
        load_scoring_rubric(RUBRIC_PATH),
    )
    assert scored.score == 0.0


def test_overlapping_employment_is_not_counted_as_separate_years() -> None:
    """PLAN 13D.5 — two concurrent Java jobs are not six years."""
    requirement = _req(
        id="req-java-years",
        text="Six years of Java backend development",
        competency="java",
    )
    northwind = _claim(
        id="claim-java-a",
        competency="java",
        context="Java backend developer at Northwind from 2019 to 2022.",
    )
    contoso = _claim(
        id="claim-java-b",
        competency="java",
        context="Java backend developer at Contoso from 2021 to 2024.",
    )
    # _claim has no dates; replace with the employment periods.
    northwind = Claim(
        id=northwind.id,
        competency=northwind.competency,
        context=northwind.context,
        duration_signal="3y",
        recency_signal="recent",
        source_span_ids=northwind.source_span_ids,
        extraction_confidence=0.9,
        period_start=date(2019, 1, 1),
        period_end=date(2022, 1, 1),
    )
    contoso = Claim(
        id=contoso.id,
        competency=contoso.competency,
        context=contoso.context,
        duration_signal="3y",
        recency_signal="recent",
        source_span_ids=contoso.source_span_ids,
        extraction_confidence=0.9,
        period_start=date(2021, 1, 1),
        period_end=date(2024, 1, 1),
    )
    result = map_requirement(requirement, (northwind, contoso))
    assert result.status is MappingStatus.PARTIAL
    assert set(result.justifying_claim_ids) == {"claim-java-a", "claim-java-b"}


def test_back_to_back_employment_still_adds_up() -> None:
    requirement = _req(
        id="req-java-years",
        text="Six years of Java backend development",
        competency="java",
    )
    first = Claim(
        id="early",
        competency="java",
        context="Java backend developer from 2018 to 2021.",
        duration_signal="3y",
        recency_signal="recent",
        source_span_ids=("early-span",),
        extraction_confidence=0.9,
        period_start=date(2018, 1, 1),
        period_end=date(2021, 1, 1),
    )
    second = Claim(
        id="later",
        competency="java",
        context="Java backend developer from 2021 to 2024.",
        duration_signal="3y",
        recency_signal="recent",
        source_span_ids=("later-span",),
        extraction_confidence=0.9,
        period_start=date(2021, 1, 1),
        period_end=date(2024, 1, 1),
    )
    result = map_requirement(requirement, (first, second))
    assert result.status is MappingStatus.MET
