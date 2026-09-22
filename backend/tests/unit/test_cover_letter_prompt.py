"""Cover letter phrasing prompt — STAR paragraphs and honest transferability."""

from __future__ import annotations

from career_assistant.application.generation.cover_letter_prompt import (
    COVER_LETTER_PROMPT_VERSION,
    cover_letter_system,
    cover_letter_user,
)


def test_cover_letter_system_teaches_star_cohesion_and_transfer() -> None:
    plain = cover_letter_system(tone="plain")
    warm = cover_letter_system(tone="warm")

    assert COVER_LETTER_PROMPT_VERSION in plain
    assert "STAR" in plain
    assert "blank line" in plain.lower() or "paragraphs" in plain.lower()
    assert "transfer" in plain.lower()
    assert "grammar" in plain.lower() or "fluent" in plain.lower()
    assert "only facts" in plain.lower() or "only" in plain.lower()
    assert "warm" in warm.lower()
    assert "plain" in plain.lower()
    assert plain != warm


def test_cover_letter_user_delimits_the_brief() -> None:
    user = cover_letter_user(briefing="MET: dbt\nEvidence: Owned dbt models.")
    assert "UNTRUSTED_COVER_LETTER_BRIEF_BEGIN" in user
    assert "UNTRUSTED_COVER_LETTER_BRIEF_END" in user
    assert "Owned dbt models." in user
    assert user.strip().endswith("Write the cover letter now.")
