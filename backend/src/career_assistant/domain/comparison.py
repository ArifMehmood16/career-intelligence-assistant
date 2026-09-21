"""Compare two roles from stored mappings — no model, no I/O."""

from __future__ import annotations

from dataclasses import dataclass

from career_assistant.domain.mapping import MappingStatus, RequirementMapping
from career_assistant.domain.requirements import Requirement

_STATUS_RANK = {
    MappingStatus.MET: 2,
    MappingStatus.PARTIAL: 1,
    MappingStatus.MISSING: 0,
}


@dataclass(frozen=True, slots=True)
class SharedRequirement:
    text: str
    a_status: MappingStatus
    b_status: MappingStatus
    must_have: bool


@dataclass(frozen=True, slots=True)
class ComparedRequirement:
    requirement: Requirement
    status: MappingStatus


@dataclass(frozen=True, slots=True)
class RoleComparison:
    shared: tuple[SharedRequirement, ...]
    only_a: tuple[ComparedRequirement, ...]
    only_b: tuple[ComparedRequirement, ...]
    differentiator: str


def compare_requirement_sets(
    *,
    title_a: str,
    title_b: str,
    requirements_a: tuple[Requirement, ...] | list[Requirement],
    mappings_a: tuple[RequirementMapping, ...] | list[RequirementMapping],
    requirements_b: tuple[Requirement, ...] | list[Requirement],
    mappings_b: tuple[RequirementMapping, ...] | list[RequirementMapping],
) -> RoleComparison:
    status_a = {item.requirement_id: item.status for item in mappings_a}
    status_b = {item.requirement_id: item.status for item in mappings_b}
    missing = MappingStatus.MISSING
    by_text_a = {
        req.text.casefold(): (req, status_a.get(req.id, missing))
        for req in requirements_a
    }
    by_text_b = {
        req.text.casefold(): (req, status_b.get(req.id, missing))
        for req in requirements_b
    }
    shared_keys = sorted(set(by_text_a) & set(by_text_b))
    only_a_keys = sorted(set(by_text_a) - set(by_text_b))
    only_b_keys = sorted(set(by_text_b) - set(by_text_a))

    shared = tuple(
        SharedRequirement(
            text=by_text_a[key][0].text,
            a_status=by_text_a[key][1],
            b_status=by_text_b[key][1],
            must_have=by_text_a[key][0].must_have or by_text_b[key][0].must_have,
        )
        for key in shared_keys
    )
    only_a = tuple(
        ComparedRequirement(requirement=by_text_a[key][0], status=by_text_a[key][1])
        for key in only_a_keys
    )
    only_b = tuple(
        ComparedRequirement(requirement=by_text_b[key][0], status=by_text_b[key][1])
        for key in only_b_keys
    )
    return RoleComparison(
        shared=shared,
        only_a=only_a,
        only_b=only_b,
        differentiator=_differentiator(title_a, title_b, shared, only_a, only_b),
    )


def _impact(must_have: bool, left: MappingStatus, right: MappingStatus) -> int:
    weight = 2 if must_have else 1
    return abs(_STATUS_RANK[left] - _STATUS_RANK[right]) * weight


def _differentiator(
    title_a: str,
    title_b: str,
    shared: tuple[SharedRequirement, ...],
    only_a: tuple[ComparedRequirement, ...],
    only_b: tuple[ComparedRequirement, ...],
) -> str:
    scored: list[tuple[int, int, str, str]] = []
    for shared_item in shared:
        gap = _impact(shared_item.must_have, shared_item.a_status, shared_item.b_status)
        if gap == 0:
            continue
        phrase = (
            f"{shared_item.text} is {shared_item.a_status.value} for {title_a} and "
            f"{shared_item.b_status.value} for {title_b}"
        )
        scored.append((gap, 1, shared_item.text.casefold(), phrase))
    for unique_a in only_a:
        other = MappingStatus.MISSING
        gap = _impact(unique_a.requirement.must_have, unique_a.status, other)
        if gap == 0:
            continue
        phrase = f"{unique_a.requirement.text} is required only for {title_a}"
        scored.append((gap, 0, unique_a.requirement.text.casefold(), phrase))
    for unique_b in only_b:
        other = MappingStatus.MISSING
        gap = _impact(unique_b.requirement.must_have, unique_b.status, other)
        if gap == 0:
            continue
        phrase = f"{unique_b.requirement.text} is required only for {title_b}"
        scored.append((gap, 0, unique_b.requirement.text.casefold(), phrase))
    if not scored:
        return "No clear differentiator"
    scored.sort(key=lambda row: (-row[0], -row[1], row[2]))
    return scored[0][3]
