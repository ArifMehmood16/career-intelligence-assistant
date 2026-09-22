"""Labelled evidence-assessment pilot for the current mapping policy.

The dataset is a reviewer's reading of synthetic passages. Loading it does not
run the matcher, and nothing in here treats a positive score as success.

``current_policy_baseline`` is the separate measurement: the hermetic path
(no embeddings, no adjudicator) compared with those labels. It does not write
back into the dataset.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from career_assistant.application.analysis.relatedness import (
    NullAdjudicator,
    map_role_requirements,
)
from career_assistant.application.ports.adjudication import AdjudicationPort
from career_assistant.application.scoring.rubric_loader import (
    load_mapping_config,
    load_scoring_rubric,
)
from career_assistant.domain.claims import Claim
from career_assistant.domain.requirements import ItemType, Requirement
from career_assistant.domain.scoring import score_fit

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


@dataclass(frozen=True, slots=True)
class AssessmentDisagreement:
    role_id: str
    requirement_id: str
    expected: str
    observed: str

    @property
    def unsupported_met(self) -> bool:
        return self.expected != "met" and self.observed == "met"


@dataclass(frozen=True, slots=True)
class OrderDisagreement:
    group_id: str
    ahead: str
    behind: str
    ahead_score: float
    behind_score: float


@dataclass(frozen=True, slots=True)
class CurrentPolicyReport:
    """Labelled pilot compared with one mapping run.

    ``current_policy_baseline`` is the hermetic run: ``calls_model`` is false.
    ``measured_policy_baseline`` records the same comparison for a supplied
    adjudicator, including per-role latency.
    """

    disagreements: tuple[AssessmentDisagreement, ...]
    order_disagreements: tuple[OrderDisagreement, ...]
    calls_model: bool
    role_latency_seconds: tuple[float, ...] = ()

    def disagreement(self, role_id: str, requirement_id: str) -> AssessmentDisagreement:
        for item in self.disagreements:
            if item.role_id == role_id and item.requirement_id == requirement_id:
                return item
        raise KeyError((role_id, requirement_id))

    @property
    def unsupported_met(self) -> tuple[AssessmentDisagreement, ...]:
        return tuple(item for item in self.disagreements if item.unsupported_met)


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


def current_policy_baseline(
    dataset: PilotDataset,
    *,
    rubric_path: Path | str | None = None,
) -> CurrentPolicyReport:
    """Score the labelled pilot with today's hermetic matcher.

    Similarities stay at 0 and the adjudicator answers nothing, which is the
    NullAdjudicator path: lexical overlap decides, and a lexical/embedding
    disagreement falls back to OR. Labels are not updated.
    """
    return measured_policy_baseline(
        dataset,
        adjudicator=NullAdjudicator(),
        rubric_path=rubric_path,
    )


def measured_policy_baseline(
    dataset: PilotDataset,
    *,
    adjudicator: AdjudicationPort,
    similarities_for: Callable[
        [Sequence[Requirement], Sequence[Claim]],
        Mapping[tuple[str, str], float],
    ]
    | None = None,
    rubric_path: Path | str | None = None,
) -> CurrentPolicyReport:
    """Score the labelled pilot with a supplied adjudicator.

    Labels are not updated. An empty similarity function is the hermetic
    retrieval path. A live run passes embeddings from the configured local model.
    """
    config_path = Path(rubric_path) if rubric_path is not None else _rubric_path()
    rubric = load_scoring_rubric(config_path)
    floor = load_mapping_config(config_path).similarity_floor
    disagreements: list[AssessmentDisagreement] = []
    order_disagreements: list[OrderDisagreement] = []
    latencies: list[float] = []
    for group in dataset.groups:
        claims = tuple(_domain_claim(claim) for claim in group.claims)
        scores: dict[str, float] = {}
        for role in group.roles:
            started = time.perf_counter()
            requirements = tuple(
                _domain_requirement(item) for item in role.requirements
            )
            similarities = (
                dict(similarities_for(requirements, claims))
                if similarities_for is not None
                else {}
            )
            mappings = map_role_requirements(
                requirements,
                claims,
                similarities=similarities,
                adjudicator=adjudicator,
                similarity_floor=floor,
            )
            observed = {
                mapping.requirement_id: mapping.status.value for mapping in mappings
            }
            for requirement in role.requirements:
                if not requirement.is_scoreable:
                    continue
                expected = role.expected_assessments[requirement.id]
                actual = observed.get(requirement.id, "missing")
                if actual != expected:
                    disagreements.append(
                        AssessmentDisagreement(
                            role_id=role.id,
                            requirement_id=requirement.id,
                            expected=expected,
                            observed=actual,
                        )
                    )
            scores[role.id] = score_fit(requirements, mappings, claims, rubric).score
            latencies.append(time.perf_counter() - started)
        order_disagreements.extend(_order_disagreements(group, scores))
    return CurrentPolicyReport(
        disagreements=tuple(disagreements),
        order_disagreements=tuple(order_disagreements),
        calls_model=bool(getattr(adjudicator, "decides_support", False)),
        role_latency_seconds=tuple(latencies),
    )


def _year_date(year: int | None) -> date | None:
    if year is None:
        return None
    return date(year, 1, 1)


def _rubric_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "config" / "scoring_rubric.toml"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("config/scoring_rubric.toml")


def _domain_requirement(item: PilotRequirement) -> Requirement:
    return Requirement(
        id=item.id,
        text=item.text,
        competency=item.competency,
        seniority_signal=item.seniority_signal,
        must_have=item.must_have,
        source_span_id=item.source_span_id,
        extraction_confidence=item.extraction_confidence,
        is_vague=item.is_vague,
        item_type=ItemType(item.item_type),
    )


def _domain_claim(item: PilotClaim) -> Claim:
    return Claim(
        id=item.id,
        competency=item.competency,
        context=item.context,
        duration_signal=item.duration_signal,
        recency_signal=item.recency_signal,
        source_span_ids=item.source_span_ids,
        extraction_confidence=item.extraction_confidence,
        self_authored=item.self_authored,
        period_start=_year_date(item.period_start),
        period_end=_year_date(item.period_end),
    )


def _order_disagreements(
    group: PilotGroup, scores: dict[str, float]
) -> list[OrderDisagreement]:
    found: list[OrderDisagreement] = []
    for constraint in group.expected_order:
        if constraint.tie:
            distinct = {scores[role_id] for role_id in constraint.tie}
            if len(distinct) > 1:
                ordered = sorted(constraint.tie, key=lambda role_id: scores[role_id])
                found.append(
                    OrderDisagreement(
                        group_id=group.id,
                        ahead=ordered[0],
                        behind=ordered[-1],
                        ahead_score=scores[ordered[0]],
                        behind_score=scores[ordered[-1]],
                    )
                )
            continue
        assert constraint.ahead is not None and constraint.behind is not None
        ahead_score = scores[constraint.ahead]
        behind_score = scores[constraint.behind]
        if ahead_score <= behind_score:
            found.append(
                OrderDisagreement(
                    group_id=group.id,
                    ahead=constraint.ahead,
                    behind=constraint.behind,
                    ahead_score=ahead_score,
                    behind_score=behind_score,
                )
            )
    return found


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
