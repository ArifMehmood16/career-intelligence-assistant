"""PLAN 13D.1 — labelled pilot and current-policy baseline.

Labels are a reviewer's reading of the passages. They are not copied from
the matcher, and a positive score is not an acceptance condition.
"""

from __future__ import annotations

import json
from pathlib import Path

from career_assistant.evaluation.baseline import current_policy_baseline, load_pilot

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


def test_current_policy_records_course_versus_leadership_as_unsupported_met() -> None:
    """The labelled pilot stays independent of the matcher.

    This records what the hermetic path gets wrong today: lexical overlap on
    "Python" marks an introductory course as meeting production leadership.
    No embedding and no adjudicator — NullAdjudicator, similarity 0.
    """
    pilot = load_pilot(DATASET)
    report = current_policy_baseline(pilot)
    course = report.disagreement("dev-insufficient-scope", "req-python-leadership")
    assert course.expected == "missing"
    assert course.observed == "met"
    assert course.unsupported_met is True
    assert report.calls_model is False
    # Observed 2026-09-22 on the hermetic path. Update with the policy, not by hand.
    assert len(report.disagreements) == 11
    assert len(report.unsupported_met) == 9
    assert len(report.order_disagreements) == 1
