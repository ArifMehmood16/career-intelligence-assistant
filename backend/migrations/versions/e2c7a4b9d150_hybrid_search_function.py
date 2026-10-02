"""v2 hybrid search as one SQL function (PLAN 18.6, ADR 013).

Dense (pgvector cosine), lexical (ts_rank over an OR-ed tsquery) and exact-term
(verified surface forms) legs over the workspace's evidence chunks, fused by
weighted reciprocal rank with ties broken on chunk id. The matching workflow, the
agent and the MCP server share it, and it runs unchanged on Supabase.
"""

from __future__ import annotations

from alembic import op

revision = "e2c7a4b9d150"
down_revision = "d3a18c0f2b61"
branch_labels = None
depends_on = None

APP_SCHEMA = "career_assistant"
EXTENSIONS_SCHEMA = "extensions"
SIGNATURE = (
    f"{APP_SCHEMA}.hybrid_search(uuid, text, {EXTENSIONS_SCHEMA}.vector, text[], "
    "text, text[], int, int, float8[], int)"
)

_FUNCTION = f"""
CREATE OR REPLACE FUNCTION {APP_SCHEMA}.hybrid_search(
  p_workspace_id    uuid,
  p_query_text      text,
  p_query_embedding {EXTENSIONS_SCHEMA}.vector,
  p_query_terms     text[],
  p_embedding_model text,
  p_sources         text[]   DEFAULT ARRAY['cv', 'cover_letter'],
  p_match_count     int      DEFAULT 8,
  p_leg_count       int      DEFAULT 20,
  p_weights         float8[] DEFAULT ARRAY[1.0, 1.0, 1.0],
  p_rrf_k           int      DEFAULT 60
)
RETURNS TABLE (chunk_id uuid, fused_score float8,
               dense_rank int, lexical_rank int, exact_rank int)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = {APP_SCHEMA}, {EXTENSIONS_SCHEMA}, public
AS $$
  WITH eligible AS (
    SELECT c.id, c.fts, c.tech_terms
    FROM chunks c JOIN documents d ON d.id = c.document_id
    WHERE c.workspace_id = p_workspace_id
      AND d.workspace_id = p_workspace_id
      AND c.evidence_eligible
      AND d.kind = ANY (p_sources)
      AND d.kind <> 'job_description'
      AND (d.kind <> 'cv' OR d.is_active)
  ),
  q AS (
    -- plainto_tsquery ANDs the lexemes; almost no bullet holds all of them.
    SELECT replace(plainto_tsquery('english', p_query_text)::text, '&', '|')::tsquery
           AS tsq
  ),
  dense AS (
    SELECT e.chunk_id,
           row_number() OVER (
             ORDER BY e.embedding <=> p_query_embedding, e.chunk_id
           )::int AS r
    FROM chunk_embeddings e JOIN eligible el ON el.id = e.chunk_id
    WHERE e.workspace_id = p_workspace_id AND e.model_key = p_embedding_model
    ORDER BY r
    LIMIT p_leg_count
  ),
  lexical AS (
    SELECT el.id AS chunk_id,
           row_number() OVER (ORDER BY ts_rank(el.fts, q.tsq) DESC, el.id)::int AS r
    FROM eligible el, q
    WHERE el.fts @@ q.tsq
    ORDER BY r
    LIMIT p_leg_count
  ),
  exact AS (
    SELECT el.id AS chunk_id,
           row_number() OVER (
             ORDER BY cardinality(ARRAY(
               SELECT unnest(el.tech_terms) INTERSECT SELECT unnest(p_query_terms)
             )) DESC,
             el.id
           )::int AS r
    FROM eligible el
    WHERE el.tech_terms && p_query_terms
    ORDER BY r
    LIMIT p_leg_count
  )
  SELECT coalesce(d.chunk_id, l.chunk_id, x.chunk_id),
         coalesce(p_weights[1] / (p_rrf_k + d.r), 0)
       + coalesce(p_weights[2] / (p_rrf_k + l.r), 0)
       + coalesce(p_weights[3] / (p_rrf_k + x.r), 0),
         d.r, l.r, x.r
  FROM dense d
  FULL JOIN lexical l ON l.chunk_id = d.chunk_id
  FULL JOIN exact   x ON x.chunk_id = coalesce(d.chunk_id, l.chunk_id)
  ORDER BY 2 DESC, 1
  LIMIT p_match_count;
$$
"""


def upgrade() -> None:
    op.execute(_FUNCTION)


def downgrade() -> None:
    op.execute(f"DROP FUNCTION IF EXISTS {SIGNATURE}")
