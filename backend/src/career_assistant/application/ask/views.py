"""Map analysis bundles into ask RoleAnalysisView."""

from __future__ import annotations

from career_assistant.application.roles.hermetic_analysis import AnalysisBundle
from career_assistant.domain.ask import RoleAnalysisView


def role_analysis_view(
    *, role_id: str, title: str, bundle: AnalysisBundle
) -> RoleAnalysisView:
    span_texts: dict[str, str] = {}
    for span in bundle.jd_spans:
        span_texts[span.id] = span.text
    for span in bundle.cv_claim_spans:
        span_texts[span.id] = span.text
    return RoleAnalysisView(
        role_id=role_id,
        title=title,
        explanation=bundle.explanation,
        requirements=bundle.requirements,
        mappings=bundle.mappings,
        span_texts=span_texts,
    )
