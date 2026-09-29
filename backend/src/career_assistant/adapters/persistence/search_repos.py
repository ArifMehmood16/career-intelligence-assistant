"""SQL adapter for the hybrid search port (ADR 013, PLAN 18.6).

The search itself is the `hybrid_search()` function, so every caller runs the
same query. This adapter shapes the lexical text and passes the parameters.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.models_v2 import RetrievalTraceRow
from career_assistant.adapters.persistence.schema import APP_SCHEMA
from career_assistant.application.ports.search import HybridQuery, RetrievalTrace
from career_assistant.domain.search import SearchHit, lexical_query_text

# Round 0 is the first search; round 1 is the one corrective rewrite (18.8).
TRACE_ROUNDS = frozenset({0, 1})
_SEARCH_SQL = text(
    "SELECT chunk_id, fused_score, dense_rank, lexical_rank, exact_rank "
    f"FROM {APP_SCHEMA}.hybrid_search("
    "CAST(:workspace_id AS uuid), :query_text, CAST(:embedding AS extensions.vector), "
    "CAST(:terms AS text[]), :model_key, CAST(:sources AS text[]), "
    ":match_count, :leg_count, CAST(:weights AS float8[]), :rrf_k)"
)


class SqlRetrievalTraceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, workspace_id: str, trace: RetrievalTrace) -> None:
        if trace.round not in TRACE_ROUNDS:
            raise ValueError(f"round must be one of {sorted(TRACE_ROUNDS)}")
        ws, verdict = uuid.UUID(workspace_id), uuid.UUID(trace.verdict_id)
        self._session.add_all(
            RetrievalTraceRow(
                workspace_id=ws,
                verdict_id=verdict,
                round=trace.round,
                query_text=trace.query_text,
                chunk_id=uuid.UUID(hit.chunk_id),
                dense_rank=hit.dense_rank,
                lexical_rank=hit.lexical_rank,
                exact_rank=hit.exact_rank,
                fused_score=hit.fused_score,
            )
            for hit in trace.hits
        )
        self._session.flush()

    def list_for_verdict(
        self, workspace_id: str, verdict_id: str
    ) -> tuple[RetrievalTrace, ...]:
        rows = self._session.scalars(
            select(RetrievalTraceRow)
            .where(
                RetrievalTraceRow.workspace_id == uuid.UUID(workspace_id),
                RetrievalTraceRow.verdict_id == uuid.UUID(verdict_id),
            )
            .order_by(
                RetrievalTraceRow.round,
                RetrievalTraceRow.fused_score.desc(),
                RetrievalTraceRow.chunk_id,
            )
        ).all()
        rounds: dict[tuple[int, str], list[SearchHit]] = {}
        for row in rows:
            rounds.setdefault((row.round, row.query_text), []).append(_hit(row))
        return tuple(
            RetrievalTrace(
                verdict_id=verdict_id, round=round_, query_text=query, hits=tuple(hits)
            )
            for (round_, query), hits in rounds.items()
        )


def _hit(row: RetrievalTraceRow) -> SearchHit:
    return SearchHit(
        chunk_id=str(row.chunk_id),
        fused_score=row.fused_score,
        dense_rank=row.dense_rank,
        lexical_rank=row.lexical_rank,
        exact_rank=row.exact_rank,
    )


class SqlHybridSearch:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def search(self, query: HybridQuery) -> tuple[SearchHit, ...]:
        weights = query.weights
        params = {
            "workspace_id": query.workspace_id,
            "query_text": lexical_query_text(query.text),
            "embedding": "[" + ",".join(repr(float(v)) for v in query.embedding) + "]",
            "terms": list(query.terms),
            "model_key": query.embedding_model_key,
            "sources": [source.value for source in query.sources],
            "match_count": query.match_count,
            "leg_count": query.leg_count,
            "weights": [weights.dense, weights.lexical, weights.exact],
            "rrf_k": query.rrf_k,
        }
        with self._session_factory() as session:
            rows = session.execute(_SEARCH_SQL, params).all()
        return tuple(
            SearchHit(
                chunk_id=str(chunk_id),
                fused_score=float(score),
                dense_rank=dense,
                lexical_rank=lexical,
                exact_rank=exact,
            )
            for chunk_id, score, dense, lexical, exact in rows
        )
