"""Publish and read back v2 analyses (ADR 014, PLAN 18.10).

A publication writes the requirement items, one verdict per requirement with its
evidence and retrieval trace, and the role's score row, in the caller's
transaction. All consumers reuse this publication and its score components.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from career_assistant.adapters.persistence.analysis_repos import (
    SqlAnalysisJobRepository,
    SqlRoleRepository,
)
from career_assistant.adapters.persistence.models import ScoreExplanationRow
from career_assistant.adapters.persistence.models_v2 import (
    ChunkRow,
    MatchVerdictRow,
    RequirementItemRow,
    VerdictEvidenceRow,
)
from career_assistant.adapters.persistence.search_repos import (
    SqlRetrievalTraceRepository,
)
from career_assistant.adapters.persistence.verdict_codec import (
    verdict_from_payload,
    verdict_payload,
)
from career_assistant.application.analysis.v2 import AnalysedRequirement, V2Analysis
from career_assistant.application.contracts.judge import JudgeResponse
from career_assistant.application.judge.prompt import JUDGE_PROMPT_VERSION
from career_assistant.application.ports.search import RetrievalTrace
from career_assistant.application.ports.v2_results import (
    StoredEvidence,
    StoredVerdict,
    V2RoleResult,
)
from career_assistant.application.ports.verdicts import VerdictRecord
from career_assistant.domain.attribution import AnalysisAttribution
from career_assistant.domain.jobs import AnalysisJob, RoleStatus
from career_assistant.domain.pipeline import PipelineVersion
from career_assistant.domain.scoring_v2 import (
    Dimension,
    FitScoreV2,
    Gap,
    KeywordCoverage,
    RequirementScore,
)

if TYPE_CHECKING:
    from career_assistant.adapters.persistence.unit_of_work import SqlUnitOfWork

EVIDENCE_DIMENSION = "match"


@dataclass(frozen=True, slots=True)
class V2Publication:
    workspace_id: str
    role_id: str
    analysis_version: int
    job: AnalysisJob
    analysis: V2Analysis
    rubric_version: str
    attribution: AnalysisAttribution


class SqlV2AnalysisRepository:
    def __init__(
        self,
        session: Session,
        roles: SqlRoleRepository,
        jobs: SqlAnalysisJobRepository,
    ) -> None:
        self._session = session
        self._roles = roles
        self._jobs = jobs

    def publish(self, publication: V2Publication) -> None:
        ws = uuid.UUID(publication.workspace_id)
        role = uuid.UUID(publication.role_id)
        analysis = publication.analysis
        self._replace_requirements(ws, role, analysis.requirements)
        scores = {
            c.requirement_id: c.requirement_score for c in analysis.fit.components
        }
        for requirement in analysis.requirements:
            record = analysis.match.verdicts.get(requirement.packet.requirement_id)
            if record is not None:
                self._add_verdict(publication, requirement, record, scores)
        self._replace_score(publication)
        self._jobs.save(publication.job)
        self._roles.set_status(
            publication.workspace_id, publication.role_id, RoleStatus.READY
        )
        self._session.flush()

    def result(self, workspace_id: str, role_id: str) -> V2RoleResult | None:
        score = self._score_row(workspace_id, role_id)
        if score is None:
            return None
        payload = score.explanation
        analysis_id = str(payload["analysis_id"])
        return V2RoleResult(
            analysis_id=analysis_id,
            score=float(score.score),
            band=score.band,
            gated=bool(payload["gated"]),
            rubric_version=score.rubric_version,
            left_machine=bool(score.left_machine),
            verdicts=self._verdicts(workspace_id, analysis_id),
            coverage=_coverage(payload["keyword_coverage"]),
            gaps=tuple(_gap(item) for item in payload["gap_plan"]),
            score_components=_score_components(payload.get("requirement_scores", [])),
        )

    def traces(
        self, workspace_id: str, role_id: str, requirement_id: str
    ) -> tuple[RetrievalTrace, ...] | None:
        score = self._score_row(workspace_id, role_id)
        try:
            requirement = uuid.UUID(requirement_id)
        except ValueError:
            return None
        if score is None:
            return None
        verdict_id = self._session.scalar(
            select(MatchVerdictRow.id).where(
                MatchVerdictRow.workspace_id == uuid.UUID(workspace_id),
                MatchVerdictRow.analysis_id
                == uuid.UUID(str(score.explanation["analysis_id"])),
                MatchVerdictRow.requirement_item_id == requirement,
            )
        )
        if verdict_id is None:
            return None
        traces = SqlRetrievalTraceRepository(self._session)
        return traces.list_for_verdict(workspace_id, str(verdict_id))

    def find_verdict(self, workspace_id: str, input_hash: str) -> VerdictRecord | None:
        row = self._session.scalar(
            select(MatchVerdictRow)
            .where(
                MatchVerdictRow.workspace_id == uuid.UUID(workspace_id),
                MatchVerdictRow.input_hash == input_hash,
            )
            .order_by(MatchVerdictRow.created_at.desc())
            .limit(1)
        )
        if row is None:
            return None
        return VerdictRecord(
            verdict=verdict_from_payload(str(row.requirement_item_id), row.payload),
            input_hash=row.input_hash,
            provider_id=row.provider,
            model_tag=row.model_tag,
            left_machine=bool(row.payload.get("left_machine", False)),
        )

    def _replace_requirements(
        self,
        ws: uuid.UUID,
        role: uuid.UUID,
        requirements: Sequence[AnalysedRequirement],
    ) -> None:
        self._session.execute(
            delete(RequirementItemRow).where(
                RequirementItemRow.workspace_id == ws,
                RequirementItemRow.role_id == role,
            )
        )
        self._session.add_all(
            RequirementItemRow(
                id=uuid.UUID(r.packet.requirement_id),
                workspace_id=ws,
                role_id=role,
                chunk_id=uuid.UUID(r.chunk_id),
                position=r.position,
                quote=r.packet.quote,
                statement=r.packet.statement,
                must_have=r.packet.must_have,
                years_expected=r.packet.years_expected,
                seniority_expected=r.packet.seniority_expected,
                tech_terms=[t.surface for t in r.tech_terms],
            )
            for r in requirements
        )
        self._session.flush()

    def _add_verdict(
        self,
        publication: V2Publication,
        requirement: AnalysedRequirement,
        record: VerdictRecord,
        scores: Mapping[str, float],
    ) -> None:
        ws = uuid.UUID(publication.workspace_id)
        verdict = record.verdict
        requirement_id = requirement.packet.requirement_id
        row = MatchVerdictRow(
            id=uuid.uuid4(),
            workspace_id=ws,
            analysis_id=uuid.UUID(publication.job.id),
            requirement_item_id=uuid.UUID(requirement_id),
            verdict=verdict.verdict,
            match_score=verdict.match_score,
            seniority_score=verdict.seniority_score,
            experience_score=verdict.experience_score,
            requirement_score=scores.get(requirement_id),
            payload=verdict_payload(verdict, left_machine=record.left_machine),
            input_hash=record.input_hash,
            provider=record.provider_id,
            model_tag=record.model_tag,
            prompt_version=JUDGE_PROMPT_VERSION,
            contract_version=JudgeResponse.contract_version,
        )
        self._session.add(row)
        self._session.flush()
        self._session.add_all(
            VerdictEvidenceRow(
                workspace_id=ws,
                verdict_id=row.id,
                chunk_id=uuid.UUID(quote.chunk_id),
                dimension=EVIDENCE_DIMENSION,
                quote=quote.quote,
            )
            for quote in verdict.evidence
        )
        traces = SqlRetrievalTraceRepository(self._session)
        for search in publication.analysis.match.traces.get(requirement_id, ()):
            traces.save(
                publication.workspace_id,
                RetrievalTrace(
                    verdict_id=str(row.id),
                    round=search.round,
                    query_text=search.query_text,
                    hits=search.hits,
                ),
            )

    def _replace_score(self, publication: V2Publication) -> None:
        ws = uuid.UUID(publication.workspace_id)
        role = uuid.UUID(publication.role_id)
        self._session.execute(
            delete(ScoreExplanationRow).where(
                ScoreExplanationRow.workspace_id == ws,
                ScoreExplanationRow.role_id == role,
                ScoreExplanationRow.analysis_version == publication.analysis_version,
            )
        )
        fit = publication.analysis.fit
        if fit.score is None:
            raise ValueError("an unscored analysis is never published")
        attribution = publication.attribution
        self._session.add(
            ScoreExplanationRow(
                id=uuid.uuid4(),
                workspace_id=ws,
                role_id=role,
                analysis_version=publication.analysis_version,
                score=fit.score,
                band=fit.band,
                explanation=_score_payload(publication),
                invalidated=False,
                assessment_provider=attribution.provider,
                assessment_model=attribution.model,
                prompt_version=attribution.prompt_version,
                rubric_version=publication.rubric_version,
                left_machine=attribution.left_machine,
                failure_status=None,
            )
        )

    def _score_row(self, workspace_id: str, role_id: str) -> ScoreExplanationRow | None:
        role = self._roles.get(workspace_id, role_id)
        if role is None:
            return None
        row = self._session.scalar(
            select(ScoreExplanationRow).where(
                ScoreExplanationRow.workspace_id == uuid.UUID(workspace_id),
                ScoreExplanationRow.role_id == uuid.UUID(role_id),
                ScoreExplanationRow.analysis_version == role.analysis_version,
                ScoreExplanationRow.invalidated.is_(False),
            )
        )
        if row is None or row.explanation.get("pipeline_version") != "v2":
            return None
        return row

    def _verdicts(
        self, workspace_id: str, analysis_id: str
    ) -> tuple[StoredVerdict, ...]:
        ws = uuid.UUID(workspace_id)
        rows = self._session.execute(
            select(MatchVerdictRow, RequirementItemRow)
            .join(
                RequirementItemRow,
                RequirementItemRow.id == MatchVerdictRow.requirement_item_id,
            )
            .join(ChunkRow, ChunkRow.id == RequirementItemRow.chunk_id)
            .where(
                MatchVerdictRow.workspace_id == ws,
                MatchVerdictRow.analysis_id == uuid.UUID(analysis_id),
            )
            .order_by(ChunkRow.first_line, RequirementItemRow.position)
        ).all()
        documents = self._documents_of(
            ws, {q["chunk_id"] for v, _ in rows for q in v.payload["evidence"]}
        )
        return tuple(_stored(verdict, item, documents) for verdict, item in rows)

    def _documents_of(self, ws: uuid.UUID, chunk_ids: set[str]) -> dict[str, str]:
        if not chunk_ids:
            return {}
        rows = self._session.execute(
            select(ChunkRow.id, ChunkRow.document_id).where(
                ChunkRow.workspace_id == ws,
                ChunkRow.id.in_([uuid.UUID(c) for c in chunk_ids]),
            )
        ).all()
        return {str(chunk_id): str(document_id) for chunk_id, document_id in rows}


class SqlVerdictCache:
    """Reuses published verdicts. `keep` is a no-op: publishing stores them."""

    def __init__(
        self, uow_factory: Callable[[], SqlUnitOfWork], workspace_id: str
    ) -> None:
        self._uow_factory = uow_factory
        self._workspace_id = workspace_id

    def find(self, key: str) -> VerdictRecord | None:
        with self._uow_factory() as uow:
            return uow.v2.find_verdict(self._workspace_id, key)

    def keep(self, key: str, record: VerdictRecord) -> None:
        return None


def _stored(
    row: MatchVerdictRow, item: RequirementItemRow, documents: Mapping[str, str]
) -> StoredVerdict:
    verdict = verdict_from_payload(str(item.id), row.payload)
    return StoredVerdict(
        requirement_id=str(item.id),
        quote=item.quote,
        statement=item.statement,
        must_have=item.must_have,
        verdict=verdict,
        requirement_score=row.requirement_score,
        evidence=tuple(
            StoredEvidence(q.chunk_id, documents.get(q.chunk_id, ""), q.quote)
            for q in verdict.evidence
        ),
        provider_id=row.provider,
        model_tag=row.model_tag,
        source_chunk_id=str(item.chunk_id),
    )


def _score_payload(publication: V2Publication) -> dict[str, Any]:
    analysis = publication.analysis
    return {
        "pipeline_version": PipelineVersion.V2.value,
        "analysis_id": publication.job.id,
        "gated": analysis.fit.gated,
        "requirement_scores": _requirement_scores(analysis.fit),
        "keyword_coverage": {
            "exact": list(analysis.coverage.exact),
            "alias": list(analysis.coverage.alias),
            "missing": list(analysis.coverage.missing),
        },
        "gap_plan": [
            {
                "requirement_id": g.requirement_id,
                "dimension": g.dimension.value,
                "current": g.current,
                "delta": g.delta,
            }
            for g in analysis.gaps
        ],
    }


def _requirement_scores(fit: FitScoreV2) -> list[dict[str, Any]]:
    return [
        {
            "requirement_id": c.requirement_id,
            "must_have": c.must_have,
            "weight": c.weight,
            "dimension_scores": {d.value: s for d, s in c.dimension_scores.items()},
            "recency_factor": c.recency_factor,
            "requirement_score": c.requirement_score,
            "contribution": c.contribution,
        }
        for c in fit.components
    ]


def _score_components(
    items: Sequence[Mapping[str, Any]],
) -> tuple[RequirementScore, ...]:
    return tuple(
        RequirementScore(
            requirement_id=str(item["requirement_id"]),
            must_have=bool(item["must_have"]),
            weight=float(item["weight"]),
            dimension_scores={
                Dimension(key): int(value)
                for key, value in item["dimension_scores"].items()
            },
            recency_factor=float(item["recency_factor"]),
            requirement_score=float(item["requirement_score"]),
            contribution=float(item["contribution"]),
        )
        for item in items
    )


def _coverage(item: Mapping[str, Sequence[str]]) -> KeywordCoverage:
    return KeywordCoverage(
        exact=tuple(item["exact"]),
        alias=tuple(item["alias"]),
        missing=tuple(item["missing"]),
    )


def _gap(item: Mapping[str, Any]) -> Gap:
    return Gap(
        requirement_id=str(item["requirement_id"]),
        dimension=Dimension(item["dimension"]),
        current=float(item["current"]),
        delta=float(item["delta"]),
    )
