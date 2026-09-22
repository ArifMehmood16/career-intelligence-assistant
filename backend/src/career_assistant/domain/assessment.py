"""Validated evidence assessment. The model proposes; this module accepts or drops.

A dropped assessment is incomplete. Callers must not turn that into a match.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

PROMPT_VERSION = "evidence-assessment-v3"
_STATUSES = frozenset({"met", "partial", "missing"})
_MAX_JUSTIFICATION = 400


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
) -> dict[str, EvidenceAssessment]:
    """Keep assessments whose spans, type and flags are valid.

    Duplicate requirement ids are dropped entirely. Unknown spans, a `met`
    assessment with a contradiction, and unparseable text return nothing for
    the affected requirement.
    """
    body = _body(payload)
    if body is None:
        return {}
    items = body.get("assessments")
    if not isinstance(items, list):
        return {}
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
            continue
        requirement_id = item.get("requirementId")
        if not isinstance(requirement_id, str) or requirement_id in duplicated:
            continue
        parsed = _one(item, allowed=allowed.get(requirement_id))
        if parsed is not None:
            accepted[requirement_id] = parsed
    return accepted


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
) -> EvidenceAssessment | None:
    if allowed is None:
        return None
    requirement_id = item.get("requirementId")
    status = item.get("assessment")
    if not isinstance(requirement_id, str) or status not in _STATUSES:
        return None
    spans = _strings(item.get("supportingSpanIds"))
    if spans is None or len(spans) != len(set(spans)):
        return None
    if any(span not in allowed for span in spans):
        return None
    if status in {"met", "partial"} and not spans:
        return None
    unmet = _strings(item.get("unmetConditions"))
    unknown = _strings(item.get("unknownConditions"))
    contradiction = item.get("contradiction")
    justification = item.get("justification")
    if unmet is None or unknown is None or not isinstance(contradiction, bool):
        return None
    if not isinstance(justification, str):
        return None
    text = justification.strip()
    if not text or len(text) > _MAX_JUSTIFICATION:
        return None
    if contradiction and status == "met":
        return None
    return EvidenceAssessment(
        requirement_id=requirement_id,
        status=status,
        supporting_span_ids=tuple(spans),
        unmet_conditions=tuple(unmet),
        unknown_conditions=tuple(unknown),
        contradiction=contradiction,
        justification=text,
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
