# Career Intelligence Assistant Constitution

## Core Principles

### I. Evidence before conclusions

The model MUST read and judge; the server MUST validate quotations and references
against stored text; pure domain code MUST compute fit. Incomplete chunking or
judging MUST publish no score or ranking position. A citation establishes provenance,
not semantic support. Generated drafts MUST NOT become scoring evidence.

### II. One running architecture

Changes MUST extend the existing chunk/search/judge pipeline and modular monolith
accepted in ADR 016. Fit, gaps, ranking, preparation, drafts, Ask and MCP MUST consume
the same validated publication. Retired v1 extraction, scoring and selection MUST NOT
be reintroduced. Domain/application code MUST depend on ports rather than frameworks
or vendor SDKs. PostgreSQL/pgvector remains the production system of record.

### III. Provider-specific execution

Ollama, OpenAI and Anthropic MUST retain separate builders/adapters and configured
model execution profiles. Application code MUST read injected capabilities instead
of branching on vendor names. Batch related work when the model's input/output
capacity permits it, reuse cached results and avoid redundant model passes. Limits
MUST reflect the selected model; no shared small budget may silently constrain all
providers. Evidence validation remains mandatory for every provider.

### IV. Bounded work and honest progress

Independent I/O MAY overlap in bounded threads; binary parsing uses bounded spawned
processes. Cancellation and progress/accounting context MUST survive thread
boundaries. Physical API attempts, retries and cached/skipped work MUST be reflected
accurately. Remaining calls MUST identify undiscovered/repair uncertainty; ETA MUST
remain unknown when timing history is unavailable. Parser processes MUST NOT receive
SQL sessions or provider objects; inherited environment is not a credential sandbox.

### V. Privacy by construction

Hosted egress MUST remain explicitly enabled and credential-gated; local remains the
default. Development/model measurements MUST use synthetic fixtures, never personal
CVs or secrets. Uploads and model output MUST be treated as untrusted. Operational
records MUST contain identifiers, counts, durations and safe codes rather than
content. Workspace scope, server-resolved citations, safe errors, attribution and
hard deletion of originals plus derived records MUST survive changes.

### VI. Incremental, evidenced delivery

Each feature MUST define a bounded change to the existing system and link to its
root PLAN/BACKLOG item, or identify the human-authorized new scope. Plans MUST reuse
existing code, dependencies and conventions before adding infrastructure. Work MUST
be committed in reviewable steps with current documentation. Only observed checks
and measurements may close gates. Explicit human deferral of tests/lint MUST be
recorded as pending verification; adoption or specification generation closes no
application release gate.

## Existing-project boundaries

The stack remains Python 3.14/FastAPI, PostgreSQL/pgvector and TypeScript/React with
TanStack Start. One CV per workspace, candidate use, English text PDF/DOCX/plain text
and narrative-only supporting letters remain current scope. OCR, auto-apply,
employer screening, a distributed queue and multi-tenancy are outside this adoption.
Deployments remain private until authentication is explicitly delivered.

Use AGENTS.md for agent operating rules; docs/features.md for product behavior;
docs/architecture.md and ADRs for accepted design; docs/api-contract.md for wire
contracts. This constitution summarizes those constraints rather than copying them.

## Development workflow

Root PLAN.md owns milestone acceptance/release gates and BACKLOG.md owns priority.
A specs/<change>/spec.md elaborates only that change's behavior and acceptance;
plan.md records its design and tasks.md records execution. These artifacts MUST link
back to the root item and MUST NOT become a second project roadmap.

Before proposing new code, inspect the affected implementation and existing tests.
Run specify, clarify where needed, plan, tasks and analyze before implementation.
Use the existing Git branch/commit workflow; automatic Git extensions are not
required. Follow current human instructions on validation timing. A deferred check
MUST stay visibly pending, and a migration MUST NOT be described as applied unless
its execution was observed.

After delivery, feature artifacts are historical change records. Later behavior
changes use a new linked feature and update current product/architecture docs;
docs/evaluation.md remains the authority for measured quality and latency.

## Governance

Direct human instructions take precedence over this constitution and AGENTS.md.
An unresolved conflict among governance or current architecture documents MUST be
stated and reconciled before dependent implementation, not silently worked around.

Amendments MUST document their reason and impact, update the version/date, and
reconcile affected feature plans and authoritative docs. Use MAJOR for incompatible
principle changes, MINOR for added/materially expanded principles, and PATCH for
clarifications. Review each feature plan against these principles and document any
human-authorized exception. Governance changes are reviewed through the existing
pull-request process; no new approval gate is introduced by this adoption.

**Version**: 1.0.0 | **Ratified**: 2026-10-02 | **Last Amended**: 2026-10-02
