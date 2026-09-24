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
