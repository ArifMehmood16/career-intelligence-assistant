"""PLAN 13D.6f — Aviva-shaped synthetic fixture safe-behaviour gates.

Hermetic and scripted only. These tests do not require a particular stochastic
fit score. They lock the shape gates: headings, benefits and logistics never
score; every labelled role and claim is preserved; incomplete assessment
publishes no score.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from career_assistant.adapters.extraction.claims_model import ModelClaimExtractor
from career_assistant.adapters.extraction.model_backed import ModelRequirementExtractor
from career_assistant.application.ports.types import (
    CapabilityDescriptor,
    CompletionRequest,
    CompletionResult,
)
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric
from career_assistant.domain.candidate_spans import candidate_units, span_id
from career_assistant.domain.documents import DocumentKind
from career_assistant.domain.mapping import (
    MappingReason,
    MappingStatus,
    RequirementMapping,
)
from career_assistant.domain.normalisation import normalise_text
from career_assistant.domain.scoring import score_fit

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "sample-data" / "fixtures" / "aviva-shaped"
AS_OF = date(2026, 9, 18)
RUBRIC = load_scoring_rubric(ROOT / "config" / "scoring_rubric.toml")


def _load(name: str) -> str:
    return normalise_text((FIXTURE / name).read_text(encoding="utf-8"))


def _labels() -> dict[str, object]:
    return json.loads((FIXTURE / "labels.json").read_text(encoding="utf-8"))


class _ScriptedCompletion:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.calls = 0

    @property
    def capabilities(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            provider_id="scripted",
            supports_completion=True,
            supports_embedding=False,
            supports_structured_output=True,
            context_window_tokens=8192,
            max_output_tokens=4096,
            embedding_dimensions=None,
            leaves_machine=False,
        )

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self.calls += 1
        return CompletionResult(
            text=json.dumps(self._payload),
            provider_id="scripted",
            model_tag="scripted-v1",
            left_machine=False,
        )


def _jd_classifications(text: str, document_id: str = "doc-jd") -> dict[str, object]:
    labels = _labels()
    skill_labels = set(labels["scoreable_skill_labels"])  # type: ignore[arg-type]
    items: list[dict[str, object]] = []
    for start, end, unit in candidate_units(text):
        issued = span_id(document_id, start, end)
        plain = unit.lstrip("* ").replace("**", "")
        if unit.rstrip().endswith(":") and "." not in unit:
            kind = "non_requirement"
            must_have = False
        elif any(
            marker.lower() in unit.lower()
            for marker in (
                "salary",
                "pension",
                "share options",
                "holiday",
                "medical",
                "bonus",
            )
        ):
            kind = "benefit"
            must_have = False
        elif any(
            marker.lower() in unit.lower()
            for marker in ("hybrid", "right to work", "edinburgh office")
        ):
            kind = "logistics"
            must_have = False
        elif any(
            plain.startswith(prefix)
            for prefix in (
                "Owning ",
                "Designing ",
                "Partnering ",
                "Building ",
                "Mentoring ",
                "Documenting ",
                "Supporting ",
            )
        ):
            kind = "responsibility"
            must_have = True
        elif any(label in unit for label in skill_labels):
            kind = "requirement"
            must_have = "Kubernetes" not in unit and "Multi-agent" not in unit
        else:
            kind = "non_requirement"
            must_have = False
        items.append(
            {
                "spanId": issued,
                "item_type": kind,
                "must_have": must_have,
                "competency": "general",
            }
        )
    return {"classifications": items}


def _cv_assignments(text: str, document_id: str = "doc-cv") -> dict[str, object]:
    labels = _labels()
    expected_employers = list(labels["expected_role_order"])  # type: ignore[arg-type]
    units = list(candidate_units(text))
    by_text = {unit: span_id(document_id, start, end) for start, end, unit in units}
    assignments: list[dict[str, object]] = []
    last_heading: str | None = None
    last_kind = "role_heading"
    for start, end, unit in units:
        issued = span_id(document_id, start, end)
        employer = next(
            (name for name in expected_employers if unit.startswith(name)),
            None,
        )
        if employer is not None:
            last_heading = issued
            last_kind = "role_heading"
            assignments.append(
                {
                    "spanId": issued,
                    "kind": "role_heading",
                    "employer": employer,
                    "title": unit.split(" — ", 1)[-1].split(",", 1)[0].strip(),
                }
            )
        elif unit.startswith("Portfolio —"):
            last_heading = issued
            last_kind = "project_heading"
            assignments.append(
                {
                    "spanId": issued,
                    "kind": "project_heading",
                    "employer": "Portfolio",
                    "title": unit.split(" — ", 1)[-1].split(",", 1)[0].strip(),
                }
            )
        elif unit.startswith("Skills:"):
            assignments.append({"spanId": issued, "kind": "skills"})
        elif last_heading is not None and (
            unit.startswith("Delivered ")
            or unit.startswith("Designed ")
            or unit.startswith("Partnered ")
            or unit.startswith("Wrote ")
            or unit.startswith("Built ")
            or unit.startswith("Authored ")
            or unit.startswith("Documented ")
            or unit.startswith("Owned ")
            or unit.startswith("Coordinated ")
            or unit.startswith("Mentored ")
            or unit.startswith("Supported ")
            or unit.startswith("Prepared ")
            or unit.startswith("Assisted ")
            or unit.startswith("Shadowed ")
            or unit.startswith("Collected ")
            or unit.startswith("Cleaned ")
            or unit.startswith("Shipped ")
            or unit.startswith("Published ")
        ):
            kind = "project" if last_kind == "project_heading" else "experience"
            assignments.append(
                {
                    "spanId": issued,
                    "kind": kind,
                    "roleSpanId": last_heading,
                }
            )
        else:
            assignments.append({"spanId": issued, "kind": "narrative"})
    assert by_text  # keep for readability / unused-guard
    return {"assignments": assignments}


def test_fixture_files_are_public_synthetic_shapes() -> None:
    labels = _labels()
    jd = (FIXTURE / str(labels["job"])).read_text(encoding="utf-8")
    cv = (FIXTURE / str(labels["cv"])).read_text(encoding="utf-8")
    assert "SYNTHETIC FIXTURE" in jd
    assert "SYNTHETIC FIXTURE" in cv
    assert "Aviva" not in jd
    assert "Aviva" not in cv
    assert "@" not in cv


def test_headings_benefits_and_logistics_never_enter_scoring() -> None:
    text = _load("jd-northbridge-mutual.txt")
    result = ModelRequirementExtractor(
        _ScriptedCompletion(_jd_classifications(text))
    ).extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=text,
    )
    assert result.complete is True
    scoreable = [req for req in result.requirements if req.is_scoreable]
    joined = " ".join(req.text for req in scoreable)
    labels = _labels()
    for marker in labels["non_scoreable_markers"]:  # type: ignore[union-attr]
        assert str(marker).lower() not in joined.lower()
    assert "You will be responsible for" not in joined
    skill_hits = [
        label
        for label in labels["scoreable_skill_labels"]  # type: ignore[union-attr]
        if any(str(label) in req.text for req in scoreable)
    ]
    assert len(skill_hits) == 8


def test_cv_preserves_six_roles_seventeen_claims_and_projects() -> None:
    text = _load("cv-jordan-hale.txt")
    result = ModelClaimExtractor(
        _ScriptedCompletion(_cv_assignments(text)),
        as_of=AS_OF,
    ).extract(
        document_id="doc-cv",
        document_kind=DocumentKind.CV,
        normalised_text=text,
    )
    labels = _labels()
    assert result.complete is True
    assert result.roles_detected == 8  # six jobs + two portfolio headings
    employers = {claim.employer for claim in result.claims}
    for name in labels["expected_role_order"]:  # type: ignore[union-attr]
        assert str(name) in employers
    experience = [claim for claim in result.claims if claim.employer != "Portfolio"]
    projects = [claim for claim in result.claims if claim.employer == "Portfolio"]
    assert len(experience) == 17
    assert len(projects) >= 2
    assert all("Kubernetes" not in claim.context for claim in result.claims)
    orchestration = next(
        claim for claim in result.claims if "orchestration" in claim.context.lower()
    )
    assert orchestration.employer in {"Cedar Grove Labs", "Portfolio"}


def test_incomplete_assessment_publishes_no_score_on_this_shape() -> None:
    jd = _load("jd-northbridge-mutual.txt")
    reqs = ModelRequirementExtractor(
        _ScriptedCompletion(_jd_classifications(jd))
    ).extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=jd,
    )
    scoreable = tuple(req for req in reqs.requirements if req.is_scoreable)
    assert scoreable
    mappings = tuple(
        RequirementMapping(
            requirement_id=req.id,
            status=MappingStatus.MISSING,
            reason_code=MappingReason.ASSESSMENT_INCOMPLETE,
            justifying_span_ids=(),
            justifying_claim_ids=(),
        )
        for req in scoreable
    )
    explanation = score_fit(scoreable, mappings, (), RUBRIC)
    assert explanation.publishable is False
    assert explanation.band == "incomplete"
    assert explanation.denominator == 0.0


def test_complete_missing_and_partial_assessments_may_publish_a_genuine_score() -> None:
    jd = _load("jd-northbridge-mutual.txt")
    reqs = ModelRequirementExtractor(
        _ScriptedCompletion(_jd_classifications(jd))
    ).extract(
        document_id="doc-jd",
        document_kind=DocumentKind.JOB_DESCRIPTION,
        normalised_text=jd,
    )
    scoreable = [req for req in reqs.requirements if req.is_scoreable]
    assert scoreable
    mappings: list[RequirementMapping] = []
    for req in scoreable:
        if "Kubernetes" in req.text:
            status, reason = MappingStatus.MISSING, MappingReason.NO_RELATED_CLAIM
        elif "Multi-agent" in req.text or "Orchestration" in req.text:
            status, reason = MappingStatus.PARTIAL, MappingReason.MATCHED
        else:
            status, reason = MappingStatus.MET, MappingReason.MATCHED
        span_ids = () if status is MappingStatus.MISSING else ("span-x",)
        claim_ids = () if status is MappingStatus.MISSING else ("claim-x",)
        mappings.append(
            RequirementMapping(
                requirement_id=req.id,
                status=status,
                reason_code=reason,
                justifying_span_ids=span_ids,
                justifying_claim_ids=claim_ids,
            )
        )
    explanation = score_fit(tuple(scoreable), tuple(mappings), (), RUBRIC)
    assert explanation.publishable is True
    assert explanation.band != "incomplete"
    # No particular score is required — only that a complete review may publish.
    assert explanation.denominator > 0.0
