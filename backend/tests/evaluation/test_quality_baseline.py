"""PLAN 13D.1 — labelled pilot and current-policy baseline.

Labels are a reviewer's reading of the passages. They are not copied from
the matcher, and a positive score is not an acceptance condition.
"""

from __future__ import annotations

import json
from pathlib import Path

from career_assistant.application.analysis.relatedness import NullAdjudicator
from career_assistant.evaluation.baseline import (
    current_policy_baseline,
    load_pilot,
    measured_policy_baseline,
)

ROOT = Path(__file__).resolve().parents[3]
DATASET = ROOT / "sample-data" / "evaluation" / "dataset.json"

REQUIRED_PHENOMENA = frozenset(
    {
        "strong_match",
        "partial_match",
        "poor_match",
        "paraphrase_no_shared_keywords",
        "insufficient_scope",
        "insufficient_duration",
        "negation",
        "overlapping_employment",
        "duplicated_requirements",
        "cv_letter_duplication",
        "contradiction",
        "aspiration",
        "injection",
        "no_scoreable_items",
    }
)


def test_pilot_covers_required_phenomena_and_both_splits() -> None:
    pilot = load_pilot(DATASET)
    assert pilot.gates.require_positive_score is False
    assert pilot.gates.require_model_wins is False
    assert pilot.gates.unsupported_met_rate_max == 0.0
    assert pilot.gates.max_completion_calls_per_role > 0
    assert pilot.gates.max_p50_latency_seconds_per_role > 0
    splits = {group.split for group in pilot.groups}
    assert splits == {"development", "held_out"}
    phenomena = {phenomenon for group in pilot.groups for phenomenon in group.phenomena}
    assert phenomena == REQUIRED_PHENOMENA
    ordered = [group for group in pilot.groups if group.expected_order]
    assert {group.split for group in ordered} == {"development", "held_out"}


def test_labels_cite_passages_and_do_not_store_matcher_output() -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    assert "observed_policy_status" not in json.dumps(payload["pilot"])
    pilot = load_pilot(DATASET)
    course = pilot.role("dev-insufficient-scope")
    assert course.expected_assessments["req-python-leadership"] == "missing"
    assert course.supporting_passages["req-python-leadership"] == ()
    heldout = pilot.role("heldout-insufficient-scope")
    assert heldout.split == "held_out"
    assert heldout.expected_assessments["req-sql-leadership"] == "missing"


def test_current_policy_does_not_score_a_course_as_leadership() -> None:
    """A course no longer comes back as meeting years of leadership.

    Observed 2026-09-22 on the hermetic path after that rule. The remaining
    disagreements are still recorded here and updated with the policy.
    """
    pilot = load_pilot(DATASET)
    report = current_policy_baseline(pilot)
    disagreed = {(item.role_id, item.requirement_id) for item in report.disagreements}
    assert ("dev-insufficient-scope", "req-python-leadership") not in disagreed
    assert ("heldout-insufficient-scope", "req-sql-leadership") not in disagreed
    assert report.calls_model is False
    assert len(report.disagreements) == 7
    assert len(report.unsupported_met) == 5
    assert len(report.order_disagreements) == 0


def test_measured_hermetic_path_matches_the_recorded_policy() -> None:
    """The same labels, with no model and no embeddings, match the hermetic baseline."""
    pilot = load_pilot(DATASET)
    measured = measured_policy_baseline(pilot, adjudicator=NullAdjudicator())
    current = current_policy_baseline(pilot)
    assert measured.calls_model is False
    assert len(measured.role_latency_seconds) == sum(
        len(group.roles) for group in pilot.groups
    )
    assert {
        (item.role_id, item.requirement_id, item.expected, item.observed)
        for item in measured.disagreements
    } == {
        (item.role_id, item.requirement_id, item.expected, item.observed)
        for item in current.disagreements
    }
    assert len(measured.order_disagreements) == len(current.order_disagreements)
