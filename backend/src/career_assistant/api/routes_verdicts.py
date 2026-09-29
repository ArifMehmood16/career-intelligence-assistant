"""A v2 analysis: per-requirement verdicts and what retrieval showed the judge.

Read-only. Every verdict and quote here passed the server's span check before it
was stored (ADR 011, ADR 013); the fit score came from domain code.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from career_assistant.api.deps import WorkspaceId
from career_assistant.api.errors import AppError
from career_assistant.api.schemas import (
    DimensionScoreWire,
    KeywordCoverageWire,
    RetrievalTraceWire,
    RoleVerdictsWire,
    TraceHitWire,
    TraceRoundWire,
    V2GapWire,
    VerdictEvidenceWire,
    VerdictWire,
)
from career_assistant.application.ports.search import RetrievalTrace
from career_assistant.application.ports.v2_results import (
    StoredVerdict,
    V2ResultReader,
    V2RoleResult,
)
from career_assistant.application.roles.store import InMemoryRoleStore
from career_assistant.domain.judging import ProposedScore

router = APIRouter(tags=["analysis"])


def _reader(request: Request) -> V2ResultReader:
    reader: V2ResultReader = request.app.state.v2_results
    return reader


def _require_role(request: Request, workspace_id: str, role_id: str) -> None:
    roles: InMemoryRoleStore = request.app.state.role_store
    if roles.get_role(workspace_id, role_id) is None:
        raise AppError("role_not_found", "No role with that id.", status_code=404)


def _dimension(score: ProposedScore | None) -> DimensionScoreWire | None:
    if score is None:
        return None
    return DimensionScoreWire(score=score.score, rationale=score.rationale)


def _verdict_wire(stored: StoredVerdict) -> VerdictWire:
    judged = stored.verdict
    return VerdictWire(
        requirement_id=stored.requirement_id,
        quote=stored.quote,
        statement=stored.statement,
        must_have=stored.must_have,
        verdict=judged.verdict,
        requirement_score=stored.requirement_score,
        match=DimensionScoreWire(
            score=judged.match_score, rationale=judged.match_rationale
        ),
        seniority=_dimension(judged.seniority),
        experience=_dimension(judged.experience),
        unmet_conditions=list(judged.unmet_conditions),
        contradiction=judged.contradiction,
        adjustments=[adjustment.value for adjustment in judged.adjustments],
        evidence=[
            VerdictEvidenceWire(
                chunk_id=item.chunk_id, document_id=item.document_id, quote=item.quote
            )
            for item in stored.evidence
        ],
        provider=stored.provider_id,
        model=stored.model_tag,
    )


def _verdicts_wire(role_id: str, result: V2RoleResult) -> RoleVerdictsWire:
    return RoleVerdictsWire(
        role_id=role_id,
        analysis_id=result.analysis_id,
        fit_score=result.score,
        band=result.band,
        gated=result.gated,
        rubric_version=result.rubric_version,
        left_machine=result.left_machine,
        verdicts=[_verdict_wire(stored) for stored in result.verdicts],
        keyword_coverage=KeywordCoverageWire(
            exact=list(result.coverage.exact),
            alias=list(result.coverage.alias),
            missing=list(result.coverage.missing),
        ),
        gap_plan=[
            V2GapWire(
                requirement_id=gap.requirement_id,
                dimension=gap.dimension.value,
                current=gap.current,
                delta=gap.delta,
            )
            for gap in result.gaps
        ],
    )


def _round_wire(trace: RetrievalTrace) -> TraceRoundWire:
    return TraceRoundWire(
        round=trace.round,
        query_text=trace.query_text,
        hits=[
            TraceHitWire(
                chunk_id=hit.chunk_id,
                fused_score=hit.fused_score,
                dense_rank=hit.dense_rank,
                lexical_rank=hit.lexical_rank,
                exact_rank=hit.exact_rank,
            )
            for hit in trace.hits
        ],
    )


@router.get("/roles/{role_id}/verdicts", response_model=RoleVerdictsWire)
def get_verdicts(
    role_id: str, request: Request, workspace_id: WorkspaceId
) -> RoleVerdictsWire:
    _require_role(request, workspace_id, role_id)
    result = _reader(request).result(workspace_id, role_id)
    if result is None:
        raise AppError(
            "analysis_incomplete",
            "No v2 analysis has finished for this role.",
            status_code=409,
        )
    return _verdicts_wire(role_id, result)


@router.get(
    "/roles/{role_id}/verdicts/{requirement_id}/trace",
    response_model=RetrievalTraceWire,
)
def get_trace(
    role_id: str, requirement_id: str, request: Request, workspace_id: WorkspaceId
) -> RetrievalTraceWire:
    _require_role(request, workspace_id, role_id)
    traces = _reader(request).traces(workspace_id, role_id, requirement_id)
    if traces is None:
        raise AppError(
            "requirement_not_found",
            "No verdict for that requirement.",
            status_code=404,
        )
    return RetrievalTraceWire(
        requirement_id=requirement_id,
        rounds=[_round_wire(trace) for trace in sorted(traces, key=_round)],
    )


def _round(trace: RetrievalTrace) -> int:
    return trace.round
