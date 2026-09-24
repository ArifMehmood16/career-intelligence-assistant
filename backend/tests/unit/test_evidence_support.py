"""Unit checks for what may justify a met or partial mapping."""

from __future__ import annotations

from career_assistant.domain.evidence_support import is_evidential_support


def test_location_headline_and_role_title_are_not_evidential() -> None:
    assert not is_evidential_support("Redditch, UK")
    assert not is_evidential_support(
        "APPLIED AI ENGINEER · PYTHON, LLM APPLICATIONS & EVALUATION · AWS · "
        "PRODUCTION SYSTEMS SINCE 2018"
    )
    assert not is_evidential_support(
        "Senior Software Engineer — Confiz Pvt Ltd Mar 2021 – Sep 2022"
    )
    assert not is_evidential_support(
        "Associate Software Engineer — Grid Systems / Global Rescue LLC "
        "Sep 2018 – Jun 2019"
    )


def test_work_bullets_and_qualifications_are_evidential() -> None:
    assert is_evidential_support(
        "Built the test coverage for AI modules sold to enterprise customers."
    )
    assert is_evidential_support(
        "Applied AI and software engineer with eight years building production "
        "systems, including an AWS platform live to 10 UK institutions."
    )
    assert is_evidential_support("AWS Certified Cloud Practitioner June 2022")
    # Product names that contain "GitHub" are work evidence, not a profile URL.
    assert is_evidential_support(
        "Set up GitHub Actions workflows that test and release the billing service."
    )


def test_references_and_boilerplate_are_not_evidential() -> None:
    assert not is_evidential_support("References available on request")
    assert not is_evidential_support("Hobbies include hiking and photography")
    assert is_evidential_support("Looked after the company's Postgres estate.")


def test_contact_handles_and_urls_are_not_evidential() -> None:
    assert not is_evidential_support("GitHub: mehmooa7")
    assert not is_evidential_support("linkedin.com/in/someone")
    assert not is_evidential_support("email me at a@example.com")


def test_common_cv_action_verbs_are_evidential() -> None:
    """2026-09-24 CV: these delivered-work lines were rejected for their verb."""
    for line in (
        "Split the payments monolith into seven services.",
        "Chose the hosting model on evidence, then handed the platform over.",
        "Compared in-house against cloud on cost and support effort.",
        "Traced faults across service boundaries and specified the fixes.",
        "Optimised the MySQL queries underneath the reports.",
        "Generated synthetic data so edge cases were exercised before release.",
        "Introduced Jira and a release process to the project.",
        "Own the release test plan with QA.",
        "Act as the technical point of contact for the whole business.",
    ):
        assert is_evidential_support(line), line

    assert not is_evidential_support("It runs on your own machine.")
    assert not is_evidential_support("Reports to the team lead weekly.")


def test_a_job_title_starting_with_lead_is_not_work_evidence() -> None:
    # Entry 120: a title cannot justify a Met. "Lead" opens titles as often as
    # it opens a duty.
    assert not is_evidential_support("Lead Software Engineer")
    assert not is_evidential_support("Lead Engineer — Acme Ltd")
    assert not is_evidential_support("- Lead Data Engineer")


def test_lead_and_own_as_a_duty_still_count() -> None:
    assert is_evidential_support("Lead a team of five engineers")
    assert is_evidential_support("Own the payments service end to end")
    assert is_evidential_support("- Owns delivery of the pricing API")


def test_a_completed_course_is_a_qualification_the_assessor_must_see() -> None:
    # ADR 010 (weak CV evidence): a responsibility, a qualification or an
    # outcome counts. The course-versus-leadership case (PLAN 13D.5) is decided
    # by the assessor and the domain, so the course line must reach them.
    assert is_evidential_support("Completed an introductory Python course.")
    assert not is_evidential_support(
        "Aspiring to lead platform engineering after a short course."
    )


def test_a_dated_role_statement_is_evidence_of_tenure() -> None:
    # A years-of-experience requirement is evidenced by the role and its dates;
    # the labelled overlap case (PLAN 13D.5) depends on these lines.
    assert is_evidential_support(
        "Java backend developer at Northwind from 2019 to 2022."
    )
    assert is_evidential_support("Senior data engineer with Contoso since 2021.")
    # A heading still names the role without showing the work (entry 120).
    assert not is_evidential_support(
        "Platform Engineer — Northwind Energy Ltd Jan 2024 – Present"
    )
    assert not is_evidential_support("Java backend developer at Northwind.")
