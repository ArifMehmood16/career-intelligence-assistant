# Architecture — one evidence-bound analysis

Current behavior, 2026-10-05. See [ADR 016](adr/016-consolidated-parallel-analysis.md)
and [PLAN 19](../PLAN.md). The retired span-classification/assessment pipeline is
implementation history, not an alternate runtime or a release dependency.

## Flow and dependencies

```mermaid
flowchart TD
  binary["Text PDF / DOCX"] --> cpu["Bounded spawned parsing"]
  plain["Plain text"] --> documents[("Stored originals and parsed text")]
  cpu --> documents
  documents --> prepare["Prepare: SQL job and current document versions"]
  prepare --> cv["Read CV: chunks, facts and technology relations"]
  prepare --> jd["Read advert: chunks and atomic requirements"]
  cv --> cvcheck["Verify line coverage and verbatim fields"]
  jd --> jdcheck["Verify line coverage and verbatim fields"]
  cvcheck --> index[("Chunks, batched vectors and full-text/graph indexes")]
  jdcheck --> index
  index --> search["Batch query embeddings; hybrid CV evidence search"]
  search --> judge["Capacity-sized judge batches; bounded threads"]
  judge --> verify["Verify anchors and evidence against retrieved stored chunks"]
  verify --> correction["Recheck thin evidence: bounded corrective search/judge"]
  correction --> score["Domain arithmetic: fit, band and gap priorities"]
  score --> complete{"Complete and current?"}
  complete -->|yes: locked publication| publication[("One validated analysis publication")]
  complete -->|no| failed["Failed analysis; no new score or ranking"]
  publication --> views["Fit / Gaps / ranking / Prepare / Letter / Ask / MCP"]
```

Independent reads overlap up to the selected execution profile. Independent judge
batches overlap up to the same bounded completion limit. A fitting document uses
one structured call: chunks, contextual search descriptions, technology terms,
atomic requirements and technology relationships come back together. Server-side
line coverage and verbatim checks run before storage. Relationships represent
inferred general knowledge and never candidate evidence.

The judge receives retrieved stored chunks and requirement facts. Input and output
budgets both determine batch size. The judge may request one better retrieval query
per requirement, bounded by the analysis rewrite cap; only changed candidate sets
are rejudged together. A failed/incomplete judgment publishes no fit score.
Fit is arithmetic over validated judgments. All product views use that result;
shared draft/citation view types do not introduce another matching/scoring path.

## Execution boundaries

- Threads overlap network/database waits. Fan-out copies cancellation, accounting
  and progress context, caps workers, preserves result order and cancels queued
  siblings after a failure. Database transactions never span model waits.
- A small process pool uses Python's spawn mode for binary document parsing. Only
  immutable document bytes/options cross the boundary; no SQL session, provider
  client or configured API key is passed as a task argument. Plain text stays
  inline. Admission checks precede dispatch; process timeout/shutdown terminates
  workers. Upload routes perform blocking work outside the HTTP event loop.
- PostgreSQL owns queued jobs, progress and results. HTTP enqueues and returns
  `202`; the bounded in-process executor claims jobs and publishes atomically.
  The existing 15-minute total running limit is checked at startup and roughly
  every five seconds during operation, including while provider calls are pending.
  This remains a single-user process with SQL-backed jobs, not a distributed queue.
- A per-document lock prevents concurrent roles indexing the same CV twice inside
  one process. Idle locks are weak references. Multi-process API deployment requires
  a database/advisory lock before it can claim the same deduplication guarantee.

## Providers and budgets

Ollama, OpenAI and Anthropic have separate transport/schema adapters. Model profiles
in [models.toml](../config/models.toml) provide context/output limits, operational
output caps, completion/embedding concurrency and estimated tokens per verdict.
The application reads these fields instead of vendor-name branches.

Ollama's local concurrency can be tuned for available hardware. OpenAI/Anthropic
use larger configured context/output budgets and a shared hosted gate that honors
response rate-limit headers. Anthropic completion uses an independent embedding
provider. Extraction/judging remain deterministic where the model supports it;
generated writing can use the adapter's supported creative controls. The schema and
evidence invariant apply equally to every provider.

Ollama embeddings use its native batched /api/embed endpoint with truncation disabled
([official API](https://docs.ollama.com/api/embed)). OpenAI already accepts batched
inputs. Model identity/dimensions permit cache checks without a probe. Cached CV
chunks/vectors and cached verdicts avoid provider calls entirely. A tag's published
limits must be configured accurately; estimates use approximate token counts.

## Progress, failure and attribution

Each stage persists states, timings, work units and planned/finished model/embedding
calls. Retries increase actual attempts. Counts omit reused/skipped work and show
undiscovered downstream work as an incomplete estimate. Repairs/splits may add
calls; the UI labels remaining calls and time as estimates. Time uses current pace
and recent measured stage durations; overlapping reads use the longest remaining
read while they run together. Without history the estimate stays unknown.

Judge/recheck requirement counts advance when a batch finishes, rather than while
individual judgments are still pending. The Fit list filters status and the stored
requirement score locally; overall fit, evidence and published ranking stay intact.

Structured output has bounded validation repair and truncation fallback. Expired,
cancelled or deleted jobs cannot publish results. Every physical retry checks
job liveness; failure recording locks and preserves terminal state. Cancellation is
cooperative: a synchronous HTTP call already sent may retain its worker thread
until it finishes or its transport times out. Citations resolve server-created spans
backed by stored chunks. Provenance records provider/model and whether content
left the machine; operational accounting holds identifiers/counts, never content.

## Job lifecycle

```mermaid
stateDiagram-v2
  [*] --> Queued: HTTP accepts the role
  Queued --> Running: Worker claims the SQL job
  Running --> Succeeded: Complete, validated, current publication
  Running --> Failed: Incomplete, provider failure, CV deletion or expiry
  Queued --> Failed: CV deleted before dispatch
  Succeeded --> [*]
  Failed --> [*]
  note right of Running
    Bounded threads; short database transactions
    Progress and physical attempts persisted
    Existing total running limit: 15 minutes
  end note
  note right of Failed
    Active task stops; no incomplete score
    Late results and retries cannot revive the job
    A prior valid publication can remain visible
  end note
```

Hard-deleting a role removes its job rows altogether; this is removal, not another
persisted job state. The read-only job endpoint can return HTTP 200 for a failed job:
clients inspect state/error and stop polling terminal outcomes. See the
[API contract](api-contract.md) and [local operations](running-locally.md).

## Storage and scope

One PostgreSQL/pgvector schema stores original documents, spans/chunks, full-text
index, vectors, graph, verdicts, score, generated drafts, chat and operational audit.
Hard deletion removes originals and derived records. Forward migrations retire the
old requirements/claims/mappings/embedding storage and obsolete analysis results;
original documents remain available for current reanalysis. The retirement upgrade
ends legacy queued/running jobs before removing their marker, preserves active current
jobs and restores an earlier valid current publication when available. Populated
migration and publication-consumer/deletion regressions pass under PLAN 19.1.
Already-applied retirement revisions cannot recover the old erased job identity.

REST/SSE, the job worker and read-only stdio MCP are entry points into the same
application services. API/worker model calls use separate provider adapters. Local
Ollama remains local; hosted calls require enabled egress and configured keys. The
MCP server reads shared SQL-backed workspace tools and does not choose a model
provider. MCP remains off by default and its client decides where returned text
goes. There is no authentication/multi-tenancy; deployments remain private and
single-user.
Quality and latency are measured only in [evaluation.md](evaluation.md).
