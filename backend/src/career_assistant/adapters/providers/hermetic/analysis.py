"""The current analysis with deterministic adapters for API tests only."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from career_assistant.adapters.providers.hermetic.embedding import (
    HermeticEmbeddingAdapter,
)
from career_assistant.adapters.providers.hermetic.index import (
    IndexBackedSearch,
    InMemoryIndexStore,
)
from career_assistant.adapters.providers.hermetic.structured import (
    HermeticStructuredCompleter,
)
from career_assistant.application.analysis.v2 import (
    RoleAnalysisV2,
    V2Documents,
    V2Limits,
)
from career_assistant.application.chunking.service import (
    ChunkingRequest,
    DocumentChunker,
)
from career_assistant.application.indexing.service import DocumentIndexer
from career_assistant.application.judge.cache import ModelIdentity
from career_assistant.application.judge.prompt import JudgeLimits
from career_assistant.application.judge.service import RequirementJudge
from career_assistant.application.ports.v2_results import (
    StoredEvidence,
    StoredVerdict,
    V2RoleResult,
)
from career_assistant.application.ports.verdicts import VerdictRecord
from career_assistant.application.roles.analysis import (
    AnalysisBundle,
    published_bundle,
    score_explanation,
)
from career_assistant.application.scoring.rubric_loader import load_scoring_rubric_v2
from career_assistant.domain.attribution import AnalysisAttribution
from career_assistant.domain.documents import DocumentKind

_RUBRIC = load_scoring_rubric_v2(
    Path(__file__).resolve().parents[6] / "config/scoring_rubric.toml"
)


class _NoCache:
    def find(self, key: str) -> VerdictRecord | None:
        return None

    def keep(self, key: str, record: VerdictRecord) -> None:
        pass


def analyse_hermetic(
    *, cv_text: str, cv_document_id: str, jd_text: str
) -> AnalysisBundle:
    jd_id, ws = str(uuid.uuid4()), "hermetic"
    store, structured, embedding = (
        InMemoryIndexStore(),
        HermeticStructuredCompleter(),
        HermeticEmbeddingAdapter(),
    )
    analysis = RoleAnalysisV2(
        indexer=DocumentIndexer(
            chunker=DocumentChunker(structured),
            embedding=embedding,
            store=store,
            max_chars_per_text=8_000,
        ),
        judge=RequirementJudge(
            structured, _NoCache(), ModelIdentity("hermetic", "rules-v1"), JudgeLimits()
        ),
        embedding=embedding,
        search=IndexBackedSearch(
            store,
            ws,
            {cv_document_id: DocumentKind.CV, jd_id: DocumentKind.JOB_DESCRIPTION},
        ),
        rubric=_RUBRIC,
        limits=V2Limits(max_rewrites=5, max_chars_per_text=8_000),
    ).run(
        V2Documents(
            workspace_id=ws,
            cv=ChunkingRequest(
                document_id=cv_document_id, kind=DocumentKind.CV, text=cv_text
            ),
            advert=ChunkingRequest(
                document_id=jd_id, kind=DocumentKind.JOB_DESCRIPTION, text=jd_text
            ),
            as_of=date.today(),
        )
    )
    if analysis.fit.score is None:
        raise ValueError("analysis_incomplete")
    chunks = tuple(item for group in store.chunks.values() for item in group)
    by_id = {item.chunk_id: item for item in chunks}
    scores = {item.requirement_id: item for item in analysis.fit.components}
    result = V2RoleResult(
        analysis_id=str(uuid.uuid4()),
        score=analysis.fit.score,
        band=analysis.fit.band,
        gated=analysis.fit.gated,
        rubric_version=_RUBRIC.version,
        left_machine=False,
        verdicts=tuple(
            StoredVerdict(
                requirement_id=item.packet.requirement_id,
                quote=item.packet.quote,
                statement=item.packet.statement,
                must_have=item.packet.must_have,
                verdict=analysis.match.verdicts[item.packet.requirement_id].verdict,
                requirement_score=scores[item.packet.requirement_id].requirement_score,
                evidence=tuple(
                    StoredEvidence(q.chunk_id, by_id[q.chunk_id].document_id, q.quote)
                    for q in analysis.match.verdicts[
                        item.packet.requirement_id
                    ].verdict.evidence
                ),
                provider_id="hermetic",
                model_tag="rules-v1",
                source_chunk_id=item.chunk_id,
            )
            for item in analysis.requirements
        ),
        coverage=analysis.coverage,
        gaps=analysis.gaps,
        score_components=analysis.fit.components,
    )
    payload: dict[str, object] = {
        "requirement_scores": [
            {
                "requirement_id": c.requirement_id,
                "must_have": c.must_have,
                "weight": c.weight,
                "requirement_score": c.requirement_score,
                "recency_factor": c.recency_factor,
                "contribution": c.contribution,
            }
            for c in analysis.fit.components
        ]
    }
    return published_bundle(
        result=result,
        chunks=chunks,
        explanation=score_explanation(result, payload),
        jd_document_id=jd_id,
        cv_document_id=cv_document_id,
        attribution=AnalysisAttribution(
            provider="hermetic",
            model="rules-v1",
            prompt_version="judge-v1",
            rubric_version=_RUBRIC.version,
            left_machine=False,
        ),
    )
