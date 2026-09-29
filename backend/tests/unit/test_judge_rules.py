"""The server's rules over a model judge's verdicts (ADR 014, PLAN 18.7)."""

from __future__ import annotations

from dataclasses import replace

from career_assistant.domain.judging import (
    Adjustment,
    Candidate,
    ProposedQuote,
    ProposedScore,
    ProposedVerdict,
    RequirementPacket,
    check_verdicts,
)

EXPERIENCE = Candidate(
    chunk_id="c1",
    kind="experience",
    source="cv",
    text="Built hybrid retrieval over\npgvector for an internal assistant.",
)
SKILLS = Candidate(
    chunk_id="c2", kind="skills", source="cv", text="Python, pgvector, dbt"
)
PACKET = RequirementPacket(
    requirement_id="r1",
    quote="Experience with vector databases",
    statement="Has used a vector database.",
    must_have=True,
    terms=("pgvector",),
    candidates=(EXPERIENCE, SKILLS),
)


def _score(score: int) -> ProposedScore:
    return ProposedScore(score=score, rationale="Because.")


def _verdict(**changes: object) -> ProposedVerdict:
    base = ProposedVerdict(
        requirement_id="r1",
        verdict="met",
        match=_score(3),
        evidence=(ProposedQuote("c1", "hybrid retrieval over pgvector"),),
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def _problems(packet: RequirementPacket, *verdicts: ProposedVerdict) -> tuple[str, ...]:
    return check_verdicts([packet], verdicts).problems.get(packet.requirement_id, ())


def test_a_valid_verdict_is_accepted_unchanged() -> None:
    check = check_verdicts([PACKET], [_verdict()])

    assert check.problems == {}
    judged = check.verdicts["r1"]
    assert (judged.verdict, judged.match_score, judged.adjustments) == ("met", 3, ())
    assert judged.evidence == (ProposedQuote("c1", "hybrid retrieval over pgvector"),)


def test_a_requirement_without_a_verdict_is_a_problem() -> None:
    check = check_verdicts([PACKET], [])

    assert check.verdicts == {}
    assert check.problems["r1"] == ("no verdict was returned",)


def test_two_verdicts_for_one_requirement_is_a_problem() -> None:
    assert _problems(PACKET, _verdict(), _verdict()) == (
        "more than one verdict was returned",
    )


def test_a_verdict_for_a_requirement_never_sent_is_refused() -> None:
    check = check_verdicts([PACKET], [_verdict(), _verdict(requirement_id="r9")])

    assert set(check.verdicts) == {"r1"}
    assert check.stray == ("r9",)


def test_citing_a_chunk_retrieval_did_not_show_is_a_problem() -> None:
    verdict = _verdict(evidence=(ProposedQuote("c9", "hybrid retrieval"),))

    assert _problems(PACKET, verdict) == (
        "evidence[0]: chunk c9 is not one of this requirement's candidates",
    )


def test_a_paraphrased_quote_is_a_problem() -> None:
    verdict = _verdict(evidence=(ProposedQuote("c1", "built retrieval on pgvector"),))

    assert _problems(PACKET, verdict) == (
        "evidence[0]: the quote is not in chunk c1 word for word",
    )


def test_a_quote_may_differ_from_its_chunk_only_in_whitespace() -> None:
    verdict = _verdict(evidence=(ProposedQuote("c1", "retrieval over  pgvector"),))

    assert _problems(PACKET, verdict) == ()


def test_credit_without_a_quote_is_a_problem() -> None:
    verdict = _verdict(verdict="partial", match=_score(2), evidence=())

    assert _problems(PACKET, verdict) == ("match: a score above 0 needs a quote",)


def test_the_verdict_and_the_match_score_must_agree() -> None:
    assert _problems(PACKET, _verdict(verdict="missing", match=_score(2))) == (
        "verdict: missing needs a match score of 0 or 1",
    )
    assert _problems(PACKET, _verdict(verdict="partial", match=_score(1))) == (
        "verdict: partial or met needs a match score of 2 or more",
    )
    assert _problems(PACKET, _verdict(verdict="met", match=_score(2))) == (
        "verdict: met needs a match score of 3 or more",
    )


def test_a_stated_level_or_number_of_years_must_be_scored() -> None:
    packet = replace(PACKET, years_expected=5.0, seniority_expected="senior")

    assert _problems(packet, _verdict()) == (
        "seniority: the requirement states a level, so score it",
        "experience: the requirement states years, so score it",
    )


def test_a_level_or_years_the_requirement_never_states_must_not_be_scored() -> None:
    verdict = _verdict(seniority=_score(3), experience=_score(3))

    assert _problems(PACKET, verdict) == (
        "seniority: the requirement states no level, so return null",
        "experience: the requirement states no years, so return null",
    )


def test_asking_for_another_search_needs_the_query() -> None:
    assert _problems(PACKET, _verdict(sufficient=False)) == (
        "retrieval_feedback: rewrite_query is required when sufficient is false",
    )


def test_a_skills_line_alone_caps_match_at_2_and_experience_at_1() -> None:
    packet = replace(PACKET, years_expected=3.0)
    verdict = _verdict(
        match=_score(4),
        experience=_score(3),
        evidence=(ProposedQuote("c2", "pgvector"),),
    )

    judged = check_verdicts([packet], [verdict]).verdicts["r1"]

    assert (judged.match_score, judged.experience_score) == (2, 1)
    assert judged.verdict == "partial"
    assert judged.adjustments == (
        Adjustment.SKILLS_ONLY_MATCH,
        Adjustment.SKILLS_ONLY_EXPERIENCE,
        Adjustment.VERDICT_LOWERED,
    )


def test_a_bare_tool_named_on_a_skills_line_may_still_be_met() -> None:
    verdict = _verdict(match=_score(4), evidence=(ProposedQuote("c2", "pgvector"),))

    judged = check_verdicts([PACKET], [verdict]).verdicts["r1"]

    assert (judged.verdict, judged.match_score) == ("met", 3)
    assert judged.adjustments == (Adjustment.SKILLS_ONLY_MATCH,)


def test_the_bare_tool_exception_needs_every_term_on_the_line() -> None:
    packet = replace(PACKET, terms=("pgvector", "qdrant"))
    verdict = _verdict(evidence=(ProposedQuote("c2", "pgvector"),))

    judged = check_verdicts([packet], [verdict]).verdicts["r1"]

    assert judged.match_score == 2


def test_the_bare_tool_exception_does_not_match_inside_another_word() -> None:
    packet = replace(PACKET, terms=("sql",))
    candidate = replace(SKILLS, text="PostgreSQL, dbt")
    packet = replace(packet, candidates=(candidate,))
    verdict = _verdict(evidence=(ProposedQuote("c2", "PostgreSQL"),))

    judged = check_verdicts([packet], [verdict]).verdicts["r1"]

    assert judged.match_score == 2


def test_skills_evidence_beside_delivery_evidence_is_not_capped() -> None:
    verdict = _verdict(
        evidence=(
            ProposedQuote("c2", "pgvector"),
            ProposedQuote("c1", "hybrid retrieval"),
        ),
        match=_score(4),
    )

    judged = check_verdicts([PACKET], [verdict]).verdicts["r1"]

    assert (judged.match_score, judged.adjustments) == (4, ())


def test_a_contradiction_caps_match_at_2_and_the_verdict_at_partial() -> None:
    judged = check_verdicts([PACKET], [_verdict(contradiction=True)]).verdicts["r1"]

    assert (judged.verdict, judged.match_score) == ("partial", 2)
    assert judged.adjustments == (
        Adjustment.CONTRADICTION_MATCH,
        Adjustment.VERDICT_LOWERED,
    )


def test_a_missing_verdict_with_no_evidence_is_valid() -> None:
    verdict = _verdict(verdict="missing", match=_score(0), evidence=())

    judged = check_verdicts([PACKET], [verdict]).verdicts["r1"]

    assert (judged.verdict, judged.match_score) == ("missing", 0)


def test_a_problem_names_ids_and_never_repeats_document_text() -> None:
    verdict = _verdict(evidence=(ProposedQuote("c1", "secret words not there"),))

    assert all("secret" not in p for p in _problems(PACKET, verdict))
