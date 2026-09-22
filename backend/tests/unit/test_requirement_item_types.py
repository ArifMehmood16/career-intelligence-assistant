"""PLAN 13C.2 — only scoreable items reach the mapping.

The 2026-09-21 audit extracted 18 "requirements" from a real advert, all
must-have, including the salary band, share options, the remote-working policy,
the right-to-work line and the three bullets under "What this role is not". The
mapping then reported that the candidate *meets* "£70,000 - £80,000 depending on
experience".

An extracted item now carries what kind of thing it is. Requirements and
responsibilities are scored; benefits, logistics and explicit non-requirements
are kept and shown but never mapped and never scored.
"""

from __future__ import annotations

from pathlib import Path

from career_assistant.application.scoring.rubric_loader import load_scoring_rubric
from career_assistant.domain.claims import Claim
from career_assistant.domain.mapping import map_requirements
from career_assistant.domain.requirements import (
    SCOREABLE_ITEM_TYPES,
    ItemType,
    Requirement,
)
from career_assistant.domain.scoring import score_fit

ROOT = Path(__file__).resolve().parents[3]
RUBRIC = load_scoring_rubric(ROOT / "config" / "scoring_rubric.toml")


def _req(
    id: str,
    text: str,
    *,
    competency: str = "general",
    item_type: ItemType = ItemType.REQUIREMENT,
) -> Requirement:
    return Requirement(
        id=id,
        text=text,
        competency=competency,
        seniority_signal=None,
        must_have=True,
        source_span_id=f"span-{id}",
        extraction_confidence=0.9,
        is_vague=False,
        item_type=item_type,
    )


def _claim(id: str, competency: str, context: str) -> Claim:
    return Claim(
        id=id,
        competency=competency,
        context=context,
        duration_signal="2y",
        recency_signal="recent",
        source_span_ids=(f"cspan-{id}",),
        extraction_confidence=0.9,
    )


def test_an_item_defaults_to_being_a_requirement() -> None:
    assert _req("r1", "Build and operate agents in production").item_type is (
        ItemType.REQUIREMENT
    )


def test_only_requirements_and_responsibilities_are_scoreable() -> None:
    assert SCOREABLE_ITEM_TYPES == frozenset(
        {ItemType.REQUIREMENT, ItemType.RESPONSIBILITY}
    )


def test_a_salary_band_is_never_mapped() -> None:
    items = [
        _req("r1", "Comfortable with APIs, JSON, webhooks and logs", competency="api"),
        _req(
            "r2",
            "£70,000 - £80,000 depending on experience",
            item_type=ItemType.BENEFIT,
        ),
    ]
    claims = [_claim("c1", "api", "Wrote the REST APIs and JSON contracts")]

    mappings = map_requirements(items, claims)

    assert {m.requirement_id for m in mappings} == {"r1"}


def test_an_explicit_non_requirement_is_never_mapped() -> None:
    items = [
        _req(
            "r1",
            "Not platform support: that's a separate function",
            item_type=ItemType.NON_REQUIREMENT,
        ),
        _req(
            "r2",
            "Full-time employee role: right to work in the UK",
            item_type=ItemType.LOGISTICS,
        ),
    ]

    assert map_requirements(items, []) == ()


def test_a_responsibility_is_scored_like_a_requirement() -> None:
    items = [
        _req(
            "r1",
            "Own production: first responder for live client agents",
            competency="ops",
            item_type=ItemType.RESPONSIBILITY,
        )
    ]
    claims = [_claim("c1", "ops", "Led production support, first responder")]

    mappings = map_requirements(items, claims)

    assert len(mappings) == 1
    assert score_fit(items, mappings, claims, RUBRIC).score > 0


def test_unscoreable_items_do_not_move_the_score() -> None:
    scoreable = [_req("r1", "Read run traces and debug", competency="ops")]
    claims = [_claim("c1", "ops", "Read the ELK traces to find the cause")]
    padded = [
        *scoreable,
        _req("r2", "Share options, awarded on performance", item_type=ItemType.BENEFIT),
        _req(
            "r3",
            "Remote (UK) with quarterly team days",
            item_type=ItemType.LOGISTICS,
        ),
    ]

    lean = score_fit(scoreable, map_requirements(scoreable, claims), claims, RUBRIC)
    fat = score_fit(padded, map_requirements(padded, claims), claims, RUBRIC)

    assert lean.score == fat.score


def test_persistence_models_carry_item_type_and_self_authored() -> None:
    from career_assistant.adapters.persistence.models import ClaimRow, RequirementRow

    assert "item_type" in RequirementRow.__table__.c
    assert "self_authored" in ClaimRow.__table__.c
