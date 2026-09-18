"""Deterministic generation artefacts — gap plan first; drafts use groundedness."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from career_assistant.domain.claims import Claim
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.requirements import Requirement
from career_assistant.domain.scoring import (
    ScoringRubric,
    counterfactual_delta,
    score_fit,
)


class GapAction(StrEnum):
    EVIDENCE_IT = "evidence_it"
    LEARN_IT = "learn_it"
    ACCEPT_IT = "accept_it"


@dataclass(frozen=True, slots=True)
class GapItem:
    requirement_id: str
    requirement_text: str
    must_have: bool
    status: MappingStatus
    reason_code: MappingReason
    score_delta: float
    action: GapAction
    adjacent_claim_ids: tuple[str, ...]
    can_draft_bullet: bool


@dataclass(frozen=True, slots=True)
class GapPlan:
    current_score: float
    items: tuple[GapItem, ...]


def build_gap_plan(
    requirements: tuple[Requirement, ...] | list[Requirement],
    mappings: tuple[RequirementMapping, ...] | list[RequirementMapping],
    claims: tuple[Claim, ...] | list[Claim],
    rubric: ScoringRubric,
) -> GapPlan:
    """Order non-met requirements by counterfactual score lift. Pure, no model."""
    by_id = {r.id: r for r in requirements}
    baseline = score_fit(requirements, mappings, claims, rubric)
    items: list[GapItem] = []
    for mapping in mappings:
        if mapping.status is MappingStatus.MET:
            continue
        req = by_id[mapping.requirement_id]
        delta = counterfactual_delta(
            requirements,
            mappings,
            claims,
            rubric,
            requirement_id=req.id,
        )
        adjacent = mapping.justifying_claim_ids
        action = _action_for(mapping, req)
        items.append(
            GapItem(
                requirement_id=req.id,
                requirement_text=req.text,
                must_have=req.must_have,
                status=mapping.status,
                reason_code=mapping.reason_code,
                score_delta=delta,
                action=action,
                adjacent_claim_ids=adjacent,
                can_draft_bullet=bool(adjacent) and action is GapAction.EVIDENCE_IT,
            )
        )
    items.sort(key=lambda item: (-item.score_delta, item.requirement_id))
    return GapPlan(current_score=baseline.score, items=tuple(items))


def _action_for(mapping: RequirementMapping, req: Requirement) -> GapAction:
    if mapping.reason_code is MappingReason.ADJACENT_CLAIM_ONLY or (
        mapping.status is MappingStatus.PARTIAL and mapping.justifying_claim_ids
    ):
        return GapAction.EVIDENCE_IT
    if not req.must_have and mapping.status is MappingStatus.MISSING:
        return GapAction.ACCEPT_IT
    return GapAction.LEARN_IT


def draft_cv_bullet_template(claim: Claim) -> str:
    """Hermetic bullet: restructure the claim sentence without inventing facts."""
    text = claim.context.strip().rstrip(".")
    if not text:
        return "- "
    # Prefer past-tense ownership phrasing when the claim already starts that way.
    return f"- {text}."


@dataclass(frozen=True, slots=True)
class CoverLetterRefusal:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class CoverLetterDraft:
    body: str
    cited_span_ids: tuple[str, ...]
    met_requirement_ids: tuple[str, ...]


def draft_cover_letter(
    *,
    role_title: str,
    company: str,
    requirements: tuple[Requirement, ...] | list[Requirement],
    mappings: tuple[RequirementMapping, ...] | list[RequirementMapping],
    claims: tuple[Claim, ...] | list[Claim],
) -> CoverLetterDraft | CoverLetterRefusal:
    """Template cover letter from met must-haves; refuses below two."""
    by_req = {r.id: r for r in requirements}
    by_claim = {c.id: c for c in claims}
    met: list[tuple[Requirement, RequirementMapping]] = []
    for mapping in mappings:
        req = by_req.get(mapping.requirement_id)
        if req is None or not req.must_have:
            continue
        if mapping.status is MappingStatus.MET:
            met.append((req, mapping))
    if len(met) < 2:
        return CoverLetterRefusal(
            code="insufficient_matched_requirements",
            message=(
                "A cover letter needs at least two met must-have requirements. "
                "Use the gap plan until more evidence is mapped."
            ),
        )
    paragraphs = [
        f"I am writing to apply for the {role_title} role at {company}.",
    ]
    cited: list[str] = []
    met_ids: list[str] = []
    for req, mapping in met:
        met_ids.append(req.id)
        claim_bits: list[str] = []
        for claim_id in mapping.justifying_claim_ids:
            claim = by_claim.get(claim_id)
            if claim is not None:
                claim_bits.append(claim.context.rstrip("."))
        cited.extend(mapping.justifying_span_ids)
        evidence = "; ".join(claim_bits) if claim_bits else req.text
        paragraphs.append(f"Regarding {req.text}: {evidence}.")
    missing = [
        by_req[m.requirement_id].text
        for m in mappings
        if m.status is not MappingStatus.MET
        and by_req.get(m.requirement_id) is not None
        and by_req[m.requirement_id].must_have
    ]
    if missing:
        paragraphs.append("I am still building depth in: " + "; ".join(missing) + ".")
    paragraphs.append("Thank you for your consideration.")
    return CoverLetterDraft(
        body="\n\n".join(paragraphs),
        cited_span_ids=tuple(dict.fromkeys(cited)),
        met_requirement_ids=tuple(met_ids),
    )


@dataclass(frozen=True, slots=True)
class InterviewProbe:
    requirement_id: str
    question: str
    status: MappingStatus


@dataclass(frozen=True, slots=True)
class InterviewLead:
    requirement_id: str
    note: str
    span_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InterviewThinArea:
    requirement_id: str
    requirement_text: str
    nearest_span_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InterviewAskThem:
    question: str
    requirement_id: str | None


@dataclass(frozen=True, slots=True)
class InterviewPack:
    probes: tuple[InterviewProbe, ...]
    lead_with: tuple[InterviewLead, ...]
    thin_areas: tuple[InterviewThinArea, ...]
    ask_them: tuple[InterviewAskThem, ...]


def build_interview_pack(
    requirements: tuple[Requirement, ...] | list[Requirement],
    mappings: tuple[RequirementMapping, ...] | list[RequirementMapping],
    claims: tuple[Claim, ...] | list[Claim],
) -> InterviewPack:
    """Section membership from the mapping; phrasing is template-only here."""
    del claims  # claims available for future evidence notes; spans come from mappings
    by_req = {r.id: r for r in requirements}
    probes: list[InterviewProbe] = []
    lead_with: list[InterviewLead] = []
    thin_areas: list[InterviewThinArea] = []
    ask_them: list[InterviewAskThem] = []

    for mapping in mappings:
        req = by_req.get(mapping.requirement_id)
        if req is None:
            continue
        if mapping.status is MappingStatus.MET:
            probes.append(
                InterviewProbe(
                    requirement_id=req.id,
                    question=f"Walk me through your experience with {req.text}.",
                    status=mapping.status,
                )
            )
            lead_with.append(
                InterviewLead(
                    requirement_id=req.id,
                    note=f"Lead with evidence for {req.text}.",
                    span_ids=mapping.justifying_span_ids,
                )
            )
        elif mapping.status is MappingStatus.PARTIAL:
            probes.append(
                InterviewProbe(
                    requirement_id=req.id,
                    question=f"Tell me about {req.text} in more depth.",
                    status=mapping.status,
                )
            )
            thin_areas.append(
                InterviewThinArea(
                    requirement_id=req.id,
                    requirement_text=req.text,
                    nearest_span_ids=mapping.justifying_span_ids,
                )
            )
        else:
            probes.append(
                InterviewProbe(
                    requirement_id=req.id,
                    question=f"How would you approach {req.text}?",
                    status=mapping.status,
                )
            )
            thin_areas.append(
                InterviewThinArea(
                    requirement_id=req.id,
                    requirement_text=req.text,
                    nearest_span_ids=(),
                )
            )
        if req.is_vague or req.extraction_confidence < 0.7:
            ask_them.append(
                InterviewAskThem(
                    question=f"What does success look like for “{req.text}”?",
                    requirement_id=req.id,
                )
            )

    return InterviewPack(
        probes=tuple(probes),
        lead_with=tuple(lead_with),
        thin_areas=tuple(thin_areas),
        ask_them=tuple(ask_them),
    )


def export_markdown(artefact: str, payload: object) -> str:
    """Deterministic markdown for screen-identical export."""
    if artefact == "gap-plan" and isinstance(payload, GapPlan):
        lines = [
            "# Gap plan",
            "",
            f"Current score: {payload.current_score:.0f}",
            "",
        ]
        for item in payload.items:
            lines.append(
                f"- **{item.requirement_text}** "
                f"({item.status.value}, Δ{item.score_delta:.1f}, "
                f"{item.action.value})"
            )
        lines.append("")
        return "\n".join(lines)
    if artefact == "interview-pack" and isinstance(payload, InterviewPack):
        lines = ["# Interview pack", "", "## Probes", ""]
        for probe in payload.probes:
            lines.append(f"- [{probe.status.value}] {probe.question}")
        lines.extend(["", "## Lead with", ""])
        for lead in payload.lead_with:
            lines.append(f"- {lead.note}")
        lines.extend(["", "## Thin areas", ""])
        for thin in payload.thin_areas:
            lines.append(f"- {thin.requirement_text}")
        lines.extend(["", "## Ask them", ""])
        for ask in payload.ask_them:
            lines.append(f"- {ask.question}")
        lines.append("")
        return "\n".join(lines)
    if artefact == "cover-letter" and isinstance(payload, CoverLetterDraft):
        return payload.body if payload.body.endswith("\n") else payload.body + "\n"
    raise ValueError(f"unsupported artefact export: {artefact!r}")
