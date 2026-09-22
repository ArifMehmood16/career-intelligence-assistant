"""Validated evidence assessment. The model proposes; this module accepts or drops.

A dropped assessment is incomplete. Callers must not turn that into a match.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

PROMPT_VERSION = "evidence-assessment-v5"
_STATUSES = frozenset({"met", "partial", "missing"})
_MAX_JUSTIFICATION = 400


@dataclass(frozen=True, slots=True)
class AssessmentBatchBudget:
    """How many requirements one assessment response may cover.

    The numbers are configuration. The adapter must not invent a batch size.
    """

    max_requirements: int
    output_tokens_per_requirement: int
    max_output_tokens: int

    def requirements_per_call(self) -> int:
        per_requirement = max(1, self.output_tokens_per_requirement)
        by_tokens = max(1, self.max_output_tokens // per_requirement)
        return max(1, min(self.max_requirements, by_tokens))


def assessment_batch_slices(count: int, per_call: int) -> tuple[tuple[int, int], ...]:
    if count <= 0:
        return ()
    size = max(1, per_call)
    return tuple((start, min(start + size, count)) for start in range(0, count, size))


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    requirement_id: str
    status: str
    supporting_span_ids: tuple[str, ...]
    unmet_conditions: tuple[str, ...]
    unknown_conditions: tuple[str, ...]
    contradiction: bool
    justification: str


def parse_assessments(
    payload: object,
    *,
    allowed: Mapping[str, frozenset[str]],
    claim_aliases: Mapping[str, frozenset[str]] | None = None,
) -> dict[str, EvidenceAssessment]:
    """Keep assessments whose spans, type and flags are valid.

    ``claim_aliases`` maps a claim id to its server span ids. Models often cite
    the claim id shown in the prompt; those expand to the claim's spans.
    Unknown ids are dropped from the citation list. Duplicate requirement ids
    are dropped entirely. A ``met`` with contradiction is dropped.
    """
    accepted, _stats = parse_assessments_with_stats(
        payload, allowed=allowed, claim_aliases=claim_aliases
    )
    return accepted


def parse_assessments_with_stats(
    payload: object,
    *,
    allowed: Mapping[str, frozenset[str]],
    claim_aliases: Mapping[str, frozenset[str]] | None = None,
) -> tuple[dict[str, EvidenceAssessment], dict[str, int]]:
    stats = {
        "returned": 0,
        "accepted": 0,
        "dropped_duplicate": 0,
        "dropped_unknown_only": 0,
        "dropped_empty_support": 0,
        "dropped_invalid": 0,
        "claim_aliases_expanded": 0,
    }
    body = _body(payload)
    if body is None:
        return {}, stats
    items = body.get("assessments")
    if not isinstance(items, list):
        return {}, stats
    stats["returned"] = len(items)
    ids = [
        item.get("requirementId")
        for item in items
        if isinstance(item, dict) and isinstance(item.get("requirementId"), str)
    ]
    duplicated = {
        requirement_id for requirement_id in ids if ids.count(requirement_id) > 1
    }
    accepted: dict[str, EvidenceAssessment] = {}
    for item in items:
        if not isinstance(item, dict):
            stats["dropped_invalid"] += 1
            continue
        requirement_id = item.get("requirementId")
        if not isinstance(requirement_id, str):
            stats["dropped_invalid"] += 1
            continue
        if requirement_id in duplicated:
            stats["dropped_duplicate"] += 1
            continue
        parsed, reason, expanded = _one(
            item,
            allowed=allowed.get(requirement_id),
            claim_aliases=claim_aliases,
        )
        if expanded:
            stats["claim_aliases_expanded"] += 1
        if parsed is None:
            stats[reason] += 1
            continue
        accepted[requirement_id] = parsed
    stats["accepted"] = len(accepted)
    return accepted, stats


def _body(payload: object) -> dict[str, object] | None:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            return None
    if not isinstance(payload, dict):
        return None
    return {str(key): value for key, value in payload.items()}


def _one(
    item: dict[str, object],
    *,
    allowed: frozenset[str] | None,
    claim_aliases: Mapping[str, frozenset[str]] | None,
) -> tuple[EvidenceAssessment | None, str, bool]:
    if allowed is None:
        return None, "dropped_invalid", False
    requirement_id = item.get("requirementId")
    status = item.get("assessment")
    if not isinstance(requirement_id, str) or status not in _STATUSES:
        return None, "dropped_invalid", False
    raw_spans = _strings(item.get("supportingSpanIds"))
    if raw_spans is None or len(raw_spans) != len(set(raw_spans)):
        return None, "dropped_invalid", False
    resolved: list[str] = []
    expanded = False
    unknown_only = False
    for cited in raw_spans:
        if cited in allowed:
            if cited not in resolved:
                resolved.append(cited)
            continue
        aliases = claim_aliases.get(cited) if claim_aliases else None
        if aliases:
            expanded = True
            for span_id in aliases:
                if span_id in allowed and span_id not in resolved:
                    resolved.append(span_id)
            continue
        unknown_only = True
    if raw_spans and not resolved:
        if status == "missing":
            resolved = []
        else:
            return None, "dropped_unknown_only", expanded
    if status in {"met", "partial"} and not resolved:
        return None, "dropped_empty_support", expanded
    unmet = _strings(item.get("unmetConditions"))
    unknown = _strings(item.get("unknownConditions"))
    contradiction = item.get("contradiction")
    justification = item.get("justification")
    if unmet is None or unknown is None or not isinstance(contradiction, bool):
        return None, "dropped_invalid", expanded
    if not isinstance(justification, str):
        return None, "dropped_invalid", expanded
    text = justification.strip()
    if not text or len(text) > _MAX_JUSTIFICATION:
        return None, "dropped_invalid", expanded
    if contradiction and status == "met":
        return None, "dropped_invalid", expanded
    # unknown_only with some valid spans: keep the valid ones.
    _ = unknown_only
    return (
        EvidenceAssessment(
            requirement_id=requirement_id,
            status=status,
            supporting_span_ids=tuple(resolved),
            unmet_conditions=tuple(unmet),
            unknown_conditions=tuple(unknown),
            contradiction=contradiction,
            justification=text,
        ),
        "accepted",
        expanded,
    )


def _strings(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    strings: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            return None
        strings.append(item)
    return strings
