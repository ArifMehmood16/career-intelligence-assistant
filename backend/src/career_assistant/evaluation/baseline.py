"""Labelled evidence-assessment pilot for the current mapping policy.

The dataset is a reviewer's reading of synthetic passages. Loading it does not
run the matcher, and nothing in here treats a positive score as success.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

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

_ASSESSMENTS = frozenset({"met", "partial", "missing"})
_SPLITS = frozenset({"development", "held_out"})
_SCOREABLE = frozenset({"requirement", "responsibility"})


@dataclass(frozen=True, slots=True)
class PilotGates:
    unsupported_met_rate_max: float
    held_out_pairwise_order_agreement_min: float
    max_completion_calls_per_role: int
    max_p50_latency_seconds_per_role: int
    max_p95_latency_seconds_per_role: int
    require_positive_score: bool
    require_model_wins: bool


@dataclass(frozen=True, slots=True)
class Passage:
    id: str
    source: str
    text: str


@dataclass(frozen=True, slots=True)
class PilotClaim:
    id: str
    competency: str
    context: str
    duration_signal: str
    recency_signal: str
    source_span_ids: tuple[str, ...]
    extraction_confidence: float
    self_authored: bool
    period_start: int | None = None
    period_end: int | None = None


@dataclass(frozen=True, slots=True)
class PilotRequirement:
    id: str
    text: str
    competency: str
    must_have: bool
    item_type: str
    seniority_signal: str | None
    source_span_id: str
    is_vague: bool
    extraction_confidence: float
    score_once_group: str | None = None

    @property
    def is_scoreable(self) -> bool:
        return self.item_type in _SCOREABLE


@dataclass(frozen=True, slots=True)
class OrderConstraint:
    ahead: str | None = None
    behind: str | None = None
    tie: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PilotRole:
    id: str
    split: str
    requirements: tuple[PilotRequirement, ...]
    expected_assessments: dict[str, str]
    supporting_passages: dict[str, tuple[str, ...]]
    expected_band: str | None = None


@dataclass(frozen=True, slots=True)
class PilotGroup:
    id: str
    split: str
    phenomena: tuple[str, ...]
    passages: tuple[Passage, ...]
    claims: tuple[PilotClaim, ...]
    roles: tuple[PilotRole, ...]
    expected_order: tuple[OrderConstraint, ...]


@dataclass(frozen=True, slots=True)
class PilotDataset:
    gates: PilotGates
    groups: tuple[PilotGroup, ...]

    def role(self, role_id: str) -> PilotRole:
        for group in self.groups:
            for role in group.roles:
                if role.id == role_id:
                    return role
        raise KeyError(role_id)


def load_pilot(path: Path | str) -> PilotDataset:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "pilot" not in payload:
        raise ValueError("dataset is missing the labelled pilot")
    pilot = payload["pilot"]
    if not isinstance(pilot, dict):
        raise ValueError("pilot must be an object")
    dataset = PilotDataset(
        gates=_gates(pilot["gates"]),
        groups=tuple(_group(item) for item in _list(pilot["groups"], "groups")),
    )
    _validate(dataset)
    return dataset


def _gates(value: object) -> PilotGates:
    raw = _mapping(value, "gates")
    gates = PilotGates(
        unsupported_met_rate_max=_float(raw["unsupported_met_rate_max"]),
        held_out_pairwise_order_agreement_min=_float(
            raw["held_out_pairwise_order_agreement_min"]
        ),
        max_completion_calls_per_role=_int(raw["max_completion_calls_per_role"]),
        max_p50_latency_seconds_per_role=_int(raw["max_p50_latency_seconds_per_role"]),
        max_p95_latency_seconds_per_role=_int(raw["max_p95_latency_seconds_per_role"]),
        require_positive_score=_bool(raw["require_positive_score"]),
        require_model_wins=_bool(raw["require_model_wins"]),
    )
    if gates.require_positive_score or gates.require_model_wins:
        raise ValueError("pilot gates must not require a positive score or a model win")
    if gates.max_completion_calls_per_role < 1:
        raise ValueError("completion call budget must be positive")
    if gates.max_p95_latency_seconds_per_role < gates.max_p50_latency_seconds_per_role:
        raise ValueError("p95 latency budget must be at least the p50 budget")
    return gates


def _group(value: object) -> PilotGroup:
    raw = _mapping(value, "group")
    split = _str(raw["split"])
    passages = tuple(_passage(item) for item in _list(raw["passages"], "passages"))
    passage_ids = {passage.id: passage for passage in passages}
    claims = tuple(_claim(item, passage_ids) for item in _list(raw["claims"], "claims"))
    roles = tuple(
        _role(item, split, passage_ids) for item in _list(raw["roles"], "roles")
    )
    return PilotGroup(
        id=_str(raw["id"]),
        split=split,
        phenomena=tuple(_str(item) for item in _list(raw["phenomena"], "phenomena")),
        passages=passages,
        claims=claims,
        roles=roles,
        expected_order=tuple(
            _order(item, {role.id for role in roles})
            for item in _list(raw["expected_order"], "expected_order")
        ),
    )


def _passage(value: object) -> Passage:
    raw = _mapping(value, "passage")
    source = _str(raw["source"])
    if source not in {"cv", "letter", "job"}:
        raise ValueError(f"unknown passage source: {source}")
    return Passage(id=_str(raw["id"]), source=source, text=_str(raw["text"]))


def _claim(value: object, passages: dict[str, Passage]) -> PilotClaim:
    raw = _mapping(value, "claim")
    span_ids = tuple(_str(item) for item in _list(raw["source_span_ids"], "spans"))
    if not span_ids:
        raise ValueError("claim must cite a passage")
    self_authored = _bool(raw["self_authored"])
    for span_id in span_ids:
        passage = passages.get(span_id)
        if passage is None:
            raise ValueError(f"claim cites unknown passage {span_id}")
        if self_authored and passage.source != "letter":
            raise ValueError("a self-authored claim must cite an uploaded letter")
        if not self_authored and passage.source != "cv":
            raise ValueError("a CV claim must cite a CV passage")
    return PilotClaim(
        id=_str(raw["id"]),
        competency=_str(raw["competency"]),
        context=_str(raw["context"]),
        duration_signal=_str(raw["duration_signal"]),
        recency_signal=_str(raw["recency_signal"]),
        source_span_ids=span_ids,
        extraction_confidence=_float(raw["extraction_confidence"]),
        self_authored=self_authored,
        period_start=_optional_int(raw.get("period_start")),
        period_end=_optional_int(raw.get("period_end")),
    )


def _role(value: object, split: str, passages: dict[str, Passage]) -> PilotRole:
    raw = _mapping(value, "role")
    requirement_items = _list(raw["requirements"], "requirements")
    requirements = tuple(_requirement(item, passages) for item in requirement_items)
    assessments = {
        _str(key): _assessment(_str(status))
        for key, status in _mapping(raw["expected_assessments"], "assessments").items()
    }
    support = {
        _str(key): tuple(_str(item) for item in _list(spans, "support"))
        for key, spans in _mapping(raw["supporting_passages"], "support").items()
    }
    for requirement in requirements:
        if requirement.is_scoreable and requirement.id not in assessments:
            raise ValueError(f"{requirement.id} has no expected assessment")
        for span_id in support.get(requirement.id, ()):
            if span_id not in passages:
                raise ValueError(f"supporting passage {span_id} is not in the group")
    return PilotRole(
        id=_str(raw["id"]),
        split=split,
        requirements=requirements,
        expected_assessments=assessments,
        supporting_passages=support,
        expected_band=_optional_str(raw.get("expected_band")),
    )


def _requirement(value: object, passages: dict[str, Passage]) -> PilotRequirement:
    raw = _mapping(value, "requirement")
    span_id = _str(raw["source_span_id"])
    passage = passages.get(span_id)
    if passage is None or passage.source != "job":
        raise ValueError(f"requirement {raw.get('id')} must cite a job passage")
    return PilotRequirement(
        id=_str(raw["id"]),
        text=_str(raw["text"]),
        competency=_str(raw["competency"]),
        must_have=_bool(raw["must_have"]),
        item_type=_str(raw["item_type"]),
        seniority_signal=_optional_str(raw.get("seniority_signal")),
        source_span_id=span_id,
        is_vague=_bool(raw["is_vague"]),
        extraction_confidence=_float(raw["extraction_confidence"]),
        score_once_group=_optional_str(raw.get("score_once_group")),
    )


def _order(value: object, role_ids: set[str]) -> OrderConstraint:
    raw = _mapping(value, "order")
    tie = tuple(_str(item) for item in _list(raw.get("tie", []), "tie"))
    ahead = _optional_str(raw.get("ahead"))
    behind = _optional_str(raw.get("behind"))
    named = [item for item in (ahead, behind, *tie) if item is not None]
    if not named:
        raise ValueError("an order constraint must name a role")
    unknown = [item for item in named if item not in role_ids]
    if unknown:
        raise ValueError(f"order cites unknown roles: {unknown}")
    if tie and (ahead or behind):
        raise ValueError("a tie constraint cannot also rank roles")
    if bool(ahead) != bool(behind):
        raise ValueError("ahead and behind must be set together")
    return OrderConstraint(ahead=ahead, behind=behind, tie=tie)


def _validate(dataset: PilotDataset) -> None:
    splits = {group.split for group in dataset.groups}
    if splits != _SPLITS:
        raise ValueError(f"pilot splits must be development and held_out, got {splits}")
    phenomena = {item for group in dataset.groups for item in group.phenomena}
    if phenomena != REQUIRED_PHENOMENA:
        missing = REQUIRED_PHENOMENA - phenomena
        extra = phenomena - REQUIRED_PHENOMENA
        raise ValueError(f"pilot phenomena mismatch, missing={missing}, extra={extra}")
    development = [group for group in dataset.groups if group.split == "development"]
    held_out = [group for group in dataset.groups if group.split == "held_out"]
    if not any(group.expected_order for group in development):
        raise ValueError("development split needs a labelled role ordering")
    if not any(group.expected_order for group in held_out):
        raise ValueError("held-out split needs a labelled role ordering")
    for group in dataset.groups:
        if group.split not in _SPLITS:
            raise ValueError(f"unknown split {group.split}")
        _validate_group(group)


def _validate_group(group: PilotGroup) -> None:
    if "overlapping_employment" in group.phenomena:
        ranges = [
            (claim.period_start, claim.period_end)
            for claim in group.claims
            if claim.period_start is not None and claim.period_end is not None
        ]
        if len(ranges) < 2 or not _ranges_overlap(ranges):
            raise ValueError(f"{group.id} labels overlap without overlapping dates")
    if "no_scoreable_items" in group.phenomena:
        for role in group.roles:
            if any(requirement.is_scoreable for requirement in role.requirements):
                raise ValueError(f"{role.id} still has a scoreable requirement")
            if role.expected_band != "unscored":
                raise ValueError(f"{role.id} must be labelled unscored")
    if "injection" in group.phenomena:
        texts = [
            requirement.text
            for role in group.roles
            for requirement in role.requirements
        ]
        if "ignore" not in " ".join(texts).lower():
            raise ValueError(f"{group.id} injection case has no instruction")
    if "duplicated_requirements" in group.phenomena:
        groups = [
            requirement.score_once_group
            for role in group.roles
            for requirement in role.requirements
            if requirement.score_once_group
        ]
        if len(groups) < 2:
            raise ValueError(f"{group.id} duplicates are not marked score-once")


def _ranges_overlap(ranges: list[tuple[int, int]]) -> bool:
    ordered = sorted(ranges)
    pairs = zip(ordered, ordered[1:], strict=False)
    return any(left[1] >= right[0] for left, right in pairs)


def _assessment(value: str) -> str:
    if value not in _ASSESSMENTS:
        raise ValueError(f"unknown assessment {value}")
    return value


def _mapping(value: object, what: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{what} must be an object")
    return {str(key): item for key, item in value.items()}


def _list(value: object, what: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{what} must be a list")
    return value


def _str(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("expected a non-empty string")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return _str(value)


def _bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise ValueError("expected a boolean")
    return value


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("expected an integer")
    return value


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return _int(value)


def _float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("expected a number")
    return float(value)
