"""SQL adapter for the hybrid search port (ADR 013, PLAN 18.6).

The search itself is the `hybrid_search()` function, so every caller runs the
same query. This adapter shapes the lexical text and passes the parameters.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from career_assistant.adapters.persistence.schema import APP_SCHEMA
from career_assistant.application.ports.search import HybridQuery
from career_assistant.domain.search import SearchHit, lexical_query_text

_SEARCH_SQL = text(
    "SELECT chunk_id, fused_score, dense_rank, lexical_rank, exact_rank "
    f"FROM {APP_SCHEMA}.hybrid_search("
    "CAST(:workspace_id AS uuid), :query_text, CAST(:embedding AS extensions.vector), "
    "CAST(:terms AS text[]), :model_key, CAST(:sources AS text[]), "
    ":match_count, :leg_count, CAST(:weights AS float8[]), :rrf_k)"
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
