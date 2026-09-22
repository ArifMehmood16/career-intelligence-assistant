# ADR 009 — Vectors propose mapping candidates; the policy decides; no chunk index

- Status: accepted
- Date: 2026-09-21

## Context

PLAN 7.2 claimed "similarity support for mapping candidates via embeddings, with
the decision still made by the policy." Three separate defects made that untrue:

1. `domain/mapping.py` `_is_related` returned on lexical overlap before the
   similarity test, and the similarity branch still required overlap, so it was
   unreachable.
2. `map_requirements` took `dict[str, float]` keyed only by claim id. Similarity
   is a requirement × claim quantity.
3. No caller computed similarities. The analysis service, hermetic in-memory
   path and SQL worker all passed `None`.

The Phase 4 schema stored 64-dimension vectors on a `chunks` table that nothing
wrote. That size matches hermetic lexical hashing, not `nomic-embed-text` (768)
or `text-embedding-3-small` (1536). PLAN 4.4 required dimensions tied to the
recorded provider/model.

Hybrid lexical/vector retrieval for Ask is a named non-goal. Phase 9 answers
from stored mappings and span retrieval.

## Decision

Embeddings cover requirement text and claim context only. There is no chunk
table and no vector retrieval for Ask.

`map_requirements` / `map_requirement` take
`similarities: Mapping[tuple[str, str], float] | None` keyed
`(requirement_id, claim_id)` and optional `adjudications` for the pairs where
lexical overlap and embedding cosine disagree. Relatedness is the domain
combination of three signals (PLAN 13C.5):

1. lexical overlap of requirement text and claim context
2. `similarity >= similarity_floor`, with the floor read from
   `config/scoring_rubric.toml` `[mapping]`
3. model adjudication of disagreements only

Agreement of (1) and (2) is final. Disagreement is a tie-break: the
adjudicator decides when it answered; hermetic analysis skips the call and
falls back to OR so embedding-only adjacent matches are not dropped. Status
remains a pure domain-policy decision. Every mapping records which signals
fired and at what strength.

A workspace holds tens of claims, so similarity is exact cosine in Python. No
ANN index. The embeddings column is dimension-agnostic and records provider,
model tag, dimensions and a sha256 of the embedded text. Changing the index
provider uses a different cache key and therefore re-embeds.

The application computes one batched `EmbeddingRequest` per analysis for uncached
texts. If the embedding port is unavailable, the egress gate refuses it, or
recorded dimensions disagree, the function returns `{}` and mapping/scoring
still complete.

## Consequences

- Adjacent claims that share no tokens can become `partial` /
  `adjacent_claim_only`; they cannot become `met` without the policy's
  competency/content rules.
- Hosted embedding dimensions (768, 1536) persist without a schema change per
  model.
- Ask behaviour is unchanged.

## Amendment — 2026-09-22

Agreement of lexical overlap and embedding cosine is retrieval, not proof of
support. [ADR 011](011-evidence-assessment-contract.md) requires a validated
assessment even when those signals agree. A missing assessment does not become
a match. The OR fallback in this ADR describes the hermetic path until that
assessment ships.
- Hard delete of a CV removes every embedding for that workspace. Role delete
  removes requirement-owned vectors. Workspace CASCADE remains the table-level
  guarantee.
