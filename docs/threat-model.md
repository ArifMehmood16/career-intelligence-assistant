# Threat model

Updated 2026-10-05 for the consolidated analysis. Uploads, questions, retrieved text,
model output and drafts remain untrusted. [ADR 016](adr/016-consolidated-parallel-analysis.md)
records the human-approved architecture. Final migration/security verification is
partly covered by passing regression checks; broader release/security work remains
open in PLAN.md.

## Trust boundaries and controls

Personal data in upload/document text, job-description text, model output and
generated drafts crosses these boundaries only under the controls below.
`create_app()` supplies in-memory provider-boundary fixtures for hermetic tests;
`create_production_app()` wires PostgreSQL adapters for the private running app.
The operational audit recorder is currently in memory; durable audit persistence
remains open work, distinct from SQL provider-call accounting.

- Browser/API: workspace cookie scoping, request schemas and configured file/question
  caps. No authentication/multi-tenancy: deployment remains private and single-user.
- Binary/parser: format sniffing and byte admission before dispatch; bounded spawned
  PDF/DOCX worker count and deadline; no macro/embedded-code execution. Only bytes
  and parse options are submitted, not SQL sessions or provider clients. Spawned
  workers inherit the host process environment, so this is CPU isolation and timeout
  control, not a security sandbox or a secrets-isolation claim.
- Documents/model: numbered stored text and retrieved tool results are delimited and
  labelled untrusted. Unified chunk/details/requirements/taxonomy output passes schema,
  line coverage and verbatim validation. Inferred technology relations never become
  candidate evidence. Validation repair and truncation fallback are bounded.
- Judge/domain: only retrieved stored chunks may support a judgment. Evidence quotes
  resolve verbatim; server caps and anchored dimensions validate the proposal. The
  domain computes scores/gaps; incomplete judgment publishes no score or rank.
  Benefit, salary and logistics chunks remain outside scored requirements.
- Provider/network: server-side keys, configured allowlist, hosted egress enforcement
  at construction and call time, explicit existing user acknowledgement, timeouts,
  circuit breakers and header-driven limits. Independent provider modules adapt their
  schemas and execution policy. Shared local-model slots bound simultaneous jobs.
- Threads/cancellation: copied context preserves job attribution and cancellation;
  queued gate waiters check liveness before provider dispatch. Already-running HTTP
  calls finish/time out and their cancelled result is discarded. SQL transactions
  stay short and never wrap model waits.
- Data/database: parameterized, workspace-scoped access; PostgreSQL/pgvector owns
  originals, chunks, vectors, graph, verdicts, drafts, chat and operational audit.
  Hard deletes remove original/derived data and citations. Retirement migration
  removes legacy derived storage, preserves original uploads/current results and
  marks affected roles for reanalysis. Downgrade restores empty schemas only.
- Output/browser: excerpts, rationales and drafts render as escaped text. Rationale
  can still misdescribe a real quote: groundedness is not a quality proof. Draft
  groundedness validates citations and unsupported content triggers refusal/fallback.
- Ask/tools: workspace-scoped read-only registry; step/tool/context budgets; agent
  citations refer only to text returned that turn and pass a verbatim check.
- MCP/client: stdio only and off by default, enabled by server-owned configuration.
  Every tool/result carries the notice that the client controls onward model egress.
- Logs/audit: allowlisted ids, counts, durations and codes only; no document, prompt,
  question/answer, model response, embedding, HTTP bodies or credentials. Progress
  persists call counts, not payloads. API keys never appear in route responses.
- Benchmark/model: an offline-default command reads only named shipped synthetic
  fixtures, with contained fixture paths and fingerprints. Explicit live opt-in
  reuses existing provider builders and hosted egress enforcement, with fallback
  disabled. Fixture storage is isolated from production, and no database URL or
  personal upload store is read. Report output allowlists metadata/counts/timing;
  transport observers retain neither URLs, headers nor bodies, and failures expose
  safe codes. Exclusive report creation prevents overwriting an existing file.

## Residual risks and limits

Model semantic errors require current labeled evaluation. ETA and pending-call counts
remain estimates; retries and undiscovered work can add calls. Token sizing is
approximate and must not trim evidence to claim success. Document index deduplication
is process-local; multi-process deployments need shared claims/locks before promising
that same guarantee. A parser timeout terminates that shared CPU pool, so simultaneous
parses may also fail safely and need retry.

The host process environment is visible to trusted spawned workers. A compromised
host/backup exposes stored personal data; private network, TLS where needed, encrypted
storage and backup policy remain deployment responsibilities. Operational audit may
be fail-open during outages. There is no malware sandbox, public log API, employer
fairness review, shared-user authorization or public deployment support in this build.

## Browser assets and container startup (2026-10-08)

The synthetic browser regression found Google Fonts requests despite local provider
selection. Font styles/binaries now come from the application origin, retaining the
same families/weights and original licenses. The real journey asserts zero external
browser requests; this is scoped evidence, not a general security claim.

Build contexts exclude personal environment files and runtime COPY is explicit.
Compose ports bind only to loopback. Migrations must succeed before API startup;
readiness checks database/schema, with safe startup errors and no raw SQL payload.
Dedicated browser tests reject non-loopback/non-`_e2e` database URLs and existing
servers; hosted credentials/gate are disabled independently of user settings.
