# ADR 013 — Model-defined chunks, hybrid search and a knowledge graph in PostgreSQL

> Runtime consolidation (2026-10-02): [ADR 016](016-consolidated-parallel-analysis.md)
> retires the competing v1 runtime and selector. References below describe the
> decision's history; the current architecture lives in [architecture.md](../architecture.md).

- Status: accepted (PLAN 18.0, 2026-09-29)
- Date: 2026-09-29
- Plan: 18.1, 18.3–18.6
- Design: [architecture.md §5–§7](../architecture.md#5-ingestion-the-model-defines-the-chunks)

## Context

v1 cuts every document into one span per line or sentence and asks the model to
classify those spans twelve at a time. The model never sees a role, a project or a
requirement block as a unit, so rules stitch them back together: PDF line reflow,
nearest-heading recovery, a delivered-work verb list, "Own" and "Lead" only as
opening words. ADR 010 gained nine amendments in three days, each patching the
consequence of the last.

Retrieval is token overlap plus an exact cosine computed in Python over
requirement and claim vectors ([ADR 009](009-vectors-propose-mapping-candidates.md)).
There is no lexical index, no fusion, and nothing an Ask question can reuse. The
`nomic-embed-text` model is called without the task prefixes it was trained with.
Exact technology names are handled by one special case for a skills line
([ADR 011](011-evidence-assessment-contract.md), 2026-09-24 amendment).

The constraint v1 got right still holds: model output must not become evidence
unless the server can find it in stored text.

## Decision

1. **The server numbers lines; the model groups them into chunks.** One structured
   call per document when it fits the provider's budget, one per server-detected
   section when it does not. A chunk is a line range, so its text is always the
   stored text. The server rejects any response that leaves a line unaccounted for,
   overlaps ranges, or exceeds the chunk size limits, and allows one repair call
   that lists the errors. A second failure makes ingestion incomplete.
2. **Model-written fields must be verbatim or they are dropped.** Technology
   surface forms, skills, employers, role titles, date text, stated years and
   requirement quotes must appear in the text they belong to, after whitespace
   normalisation; a bullet's role fields are checked against the role heading it
   references. Dates are parsed in domain code. A job-description chunk carries
   atomic requirements, each with its verbatim clause. A canonical spelling, a
   role's level and a restated requirement are interpretations, stored and shown as
   such.
3. **Contextual retrieval.** Each chunk gets a model-written context header that is
   prepended for embedding and full-text indexing only. It is never displayed as
   evidence and never quotable.
4. **Hybrid search is one SQL function.** A dense leg (pgvector cosine over
   prefix-aware embeddings), a lexical leg (PostgreSQL full-text search, an
   OR-of-lexemes `tsquery` without generic requirement words, ranked by `ts_rank`)
   and an exact-term leg (verified technology surface forms with GIN overlap; the
   model's canonical spellings are inferred aliases that only widen the query) are
   fused by weighted reciprocal rank, with ties broken on chunk id. Matching stores
   each search's trace: query, terms, per-leg ranks and fused score.
5. **The dense leg is an exact scan** over one workspace's vectors, served by a
   B-tree on `(workspace_id, model_key)`. A workspace holds tens to hundreds of
   chunks and the product never searches across workspaces. An approximate index is
   the documented path if one workspace ever grows large; it is not built.
6. **A knowledge graph lives in two PostgreSQL tables.** Asserted edges come from
   validated chunks and cite them. Inferred edges come from the model's general
   knowledge, cite nothing, and may only widen a search. Years of experience are
   computed in domain code as the union of the parsed date intervals of the roles
   linked to a technology or skill, labelled as an upper bound. Graph rows record
   the document they came from and are deleted with it.
7. **Embeddings know their input type.** `EmbeddingRequest` carries `query` or
   `document`; vectors are keyed by provider, model, dimensions and input type.

This supersedes ADR 009's "no chunk table and no vector retrieval for Ask", and the
line and sentence segmentation contract in ADR 010's 2026-09-22 amendments, once
Phase 18.15 retires the v1 path. Until then both run side by side and each analysis
records its `pipeline_version`.

## Consequences

- The model sees whole roles and requirement blocks. Wrapped PDF lines are two
  lines in one chunk, so the reflow heuristics can retire if the evaluation agrees.
- Fabricated evidence is still bounded by the server: a chunk cannot contain words
  the document does not, and a technology the candidate never wrote is dropped.
- A dropped line is a failed ingestion, not a silent gap. That is stricter than v1,
  which could drop an unclassifiable span and carry on.
- Retrieval becomes inspectable and reusable: the matching workflow, the agent and
  the MCP server all call the same function.
- One more model call type (chunking) and one small one (inferred edges for new
  technology terms). Both are recorded in provider-call accounting.
- The same migrations and `hybrid_search()` run on a Supabase project, with
  pgvector in the `extensions` schema; a CI job against Supabase's Postgres image
  proves it.
- Hard delete gains chunks, chunk embeddings, requirement items, graph nodes and
  edges, verdicts and retrieval traces. Each cascades from the document or role it
  came from.

## Rejected alternatives

- **Fixed-size or recursive character chunking.** Cheap and model-free, but it cuts
  roles in half and has no idea what a requirement is. The whole point is that
  deciding the unit is a language task.
- **Let the model return chunk text.** It would paraphrase, and a paraphrase is a
  fabricated span. Line ranges keep the text server-owned.
- **Weighted sum of raw scores instead of RRF.** A cosine, a `ts_rank` and a term
  count are on different scales; normalising them is its own tuning problem. RRF
  needs only ranks.
- **A dedicated vector database or a graph database.** Either breaks
  one-transaction hard delete, adds a backup and access story, and is not available
  on Supabase. The data is small and the traversals are two hops.
- **BM25 through ParadeDB's `pg_search`.** Better lexical ranking, but it is not one
  of the extensions a Supabase project ships with, so it would mean a second
  database. Native full-text search is the default; BM25 is the swap to evaluate if
  18.14 shows the lexical leg is the bottleneck.
- **`ts_rank_cd` for the lexical leg.** With an OR query it scored a chunk that
  repeats one word above a chunk that covers three of them (checked on PostgreSQL
  16). `ts_rank` rewards coverage.
- **A synonym list for technologies.** Inferred graph edges widen the search and the
  judge decides; nothing rewrites one technology into another.
