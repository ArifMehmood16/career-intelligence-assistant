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
                can_draft_bullet=mapping_supports_cv_bullet(mapping),
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


def mapping_supports_cv_bullet(mapping: RequirementMapping) -> bool:
    """Adjacent evidence is not enough to draft a cited bullet for that requirement."""
    if not mapping.justifying_claim_ids:
        return False
    return mapping.reason_code is not MappingReason.ADJACENT_CLAIM_ONLY


def draft_cv_bullet_template(claim: Claim) -> str:
    """Hermetic bullet: restructure the claim sentence without inventing facts."""
    text = claim.context.strip().rstrip(".")
    if not text:
        return "- "
    # Prefer past-tense ownership phrasing when the claim already starts that way.
    return f"- {text}."


@dataclass(frozen=True, slots=True)
class FitSummary:
    text: str
    strongest_requirement_id: str | None
    weakest_requirement_id: str | None


def build_fit_summary(
    requirements: tuple[Requirement, ...] | list[Requirement],
    mappings: tuple[RequirementMapping, ...] | list[RequirementMapping],
    claims: tuple[Claim, ...] | list[Claim],
    rubric: ScoringRubric,
) -> FitSummary:
    """Name the strongest match and biggest gap from the scored mapping. Pure."""
    by_id = {req.id: req for req in requirements if req.is_scoreable}
    scoreable = tuple(
        mapping for mapping in mappings if mapping.requirement_id in by_id
    )
    explanation = score_fit(tuple(by_id.values()), scoreable, claims, rubric)
    met = [
        component
        for component in explanation.components
        if component.status is MappingStatus.MET
    ]
    met.sort(
        key=lambda component: (
            -component.contribution,
            0 if component.must_have else 1,
            component.requirement_id,
        )
    )
    strongest = met[0].requirement_id if met else None
    plan = build_gap_plan(tuple(by_id.values()), scoreable, claims, rubric)
    weakest = plan.items[0].requirement_id if plan.items else None
    return FitSummary(
        text=_fit_summary_text(by_id, strongest, weakest),
        strongest_requirement_id=strongest,
        weakest_requirement_id=weakest,
    )


def _fit_summary_text(
    by_id: dict[str, Requirement],
    strongest: str | None,
    weakest: str | None,
) -> str:
    strong_text = by_id[strongest].text if strongest is not None else None
    weak_text = by_id[weakest].text if weakest is not None else None
    if strong_text and weak_text:
        return (
            f"The strongest match is “{strong_text}”. The biggest gap is “{weak_text}”."
        )
    if strong_text:
        return (
            f"The strongest match is “{strong_text}”. "
            "There are no remaining scored gaps."
        )
    if weak_text:
        return f"No scored requirement is met yet. The biggest gap is “{weak_text}”."
    return "No scored requirements are available for this role."


@dataclass(frozen=True, slots=True)
class CoverLetterRefusal:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class CoverLetterDraft:
    body: str
    cited_span_ids: tuple[str, ...]
    met_requirement_ids: tuple[str, ...]


_MAX_MET_PARAGRAPHS = 4
_MAX_TRANSFER_PARAGRAPHS = 2


def draft_cover_letter(
    *,
    role_title: str,
    company: str,
    requirements: tuple[Requirement, ...] | list[Requirement],
    mappings: tuple[RequirementMapping, ...] | list[RequirementMapping],
    claims: tuple[Claim, ...] | list[Claim],
    tone: str = "plain",
    include_gap_line: bool = False,
) -> CoverLetterDraft | CoverLetterRefusal:
    """Template cover letter from met must-haves; refuses below two.

    The body is both the hermetic fallback and the brief the model rephrases.
    It prioritises the strongest met must-haves, then transferable partial
    evidence for gaps, without inventing experience.
    """
    by_req = {r.id: r for r in requirements}
    by_claim = {c.id: c for c in claims}
    met: list[tuple[Requirement, RequirementMapping]] = []
    transferable: list[tuple[Requirement, RequirementMapping]] = []
    bare_gaps: list[str] = []
    for mapping in mappings:
        req = by_req.get(mapping.requirement_id)
        if req is None or not req.must_have:
            continue
        if mapping.status is MappingStatus.MET:
            met.append((req, mapping))
        elif mapping.justifying_claim_ids:
            transferable.append((req, mapping))
        else:
            bare_gaps.append(req.text)
    if len(met) < 2:
        return CoverLetterRefusal(
            code="insufficient_matched_requirements",
            message=(
                "A cover letter needs at least two met must-have requirements. "
                "Use the gap plan until more evidence is mapped."
            ),
        )
    opening = (
        f"I would be glad to apply for the {role_title} role at {company}."
        if tone == "warm"
        else f"I am writing to apply for the {role_title} role at {company}."
    )
    paragraphs = [opening]
    cited: list[str] = []
    met_ids: list[str] = []
    for req, mapping in met[:_MAX_MET_PARAGRAPHS]:
        met_ids.append(req.id)
        evidence = _claim_evidence(mapping, by_claim)
        cited.extend(mapping.justifying_span_ids)
        if evidence:
            paragraphs.append(
                "MET\n"
                f"Requirement: {req.text}\n"
                f"Evidence: {evidence}\n"
                f"In that work I took ownership of the need around {req.text}, "
                f"acted through {evidence}, and delivered a concrete result "
                "recorded in my CV."
            )
        else:
            paragraphs.append(
                "MET\n"
                f"Requirement: {req.text}\n"
                f"Evidence: {req.text}"
            )
    for req, mapping in transferable[:_MAX_TRANSFER_PARAGRAPHS]:
        evidence = _claim_evidence(mapping, by_claim)
        if not evidence:
            continue
        cited.extend(mapping.justifying_span_ids)
        paragraphs.append(
            "TRANSFER\n"
            f"Requirement: {req.text}\n"
            f"Nearby evidence: {evidence}\n"
            f"I have not yet covered {req.text} end to end, but {evidence} "
            "is directly transferable to that requirement."
        )
    if include_gap_line and bare_gaps:
        paragraphs.append(
            "GAP\n"
            "I am still building depth in: " + "; ".join(bare_gaps) + "."
        )
    paragraphs.append("Thank you for your consideration.")
    return CoverLetterDraft(
        body="\n\n".join(paragraphs),
        cited_span_ids=tuple(dict.fromkeys(cited)),
        met_requirement_ids=tuple(met_ids),
    )


def _claim_evidence(
    mapping: RequirementMapping,
    by_claim: dict[str, Claim],
) -> str:
    bits: list[str] = []
    for claim_id in mapping.justifying_claim_ids:
        claim = by_claim.get(claim_id)
        if claim is not None:
            bits.append(claim.context.rstrip("."))
    return "; ".join(bits)


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
    """Section membership from the mapping; phrasing quotes the candidate's claims."""
    by_req = {r.id: r for r in requirements}
    by_claim = {claim.id: claim for claim in claims}
    probes: list[InterviewProbe] = []
    lead_with: list[InterviewLead] = []
    thin_areas: list[InterviewThinArea] = []
    ask_them: list[InterviewAskThem] = []

    for mapping in mappings:
        req = by_req.get(mapping.requirement_id)
        if req is None:
            continue
        evidence = _primary_claim_context(mapping, by_claim)
        if mapping.status is MappingStatus.MET:
            probes.append(
                InterviewProbe(
                    requirement_id=req.id,
                    question=(
                        f"Walk me through “{evidence}” as evidence of {req.text}."
                        if evidence
                        else f"Walk me through your experience with {req.text}."
                    ),
                    status=mapping.status,
                )
            )
            lead_with.append(
                InterviewLead(
                    requirement_id=req.id,
                    note=(
                        f"Lead with: “{evidence}”"
                        if evidence
                        else f"Lead with evidence for {req.text}."
                    ),
                    span_ids=mapping.justifying_span_ids,
                )
            )
        elif mapping.status is MappingStatus.PARTIAL:
            probes.append(
                InterviewProbe(
                    requirement_id=req.id,
                    question=(
                        f"Tell me more about {req.text} beyond “{evidence}”."
                        if evidence
                        else f"Tell me about {req.text} in more depth."
                    ),
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


def _primary_claim_context(
    mapping: RequirementMapping, by_claim: dict[str, Claim]
) -> str | None:
    for claim_id in mapping.justifying_claim_ids:
        claim = by_claim.get(claim_id)
        if claim is None:
            continue
        text = claim.context.strip()
        if text:
            return text
    return None
