# Threat model

Updated 2026-10-02 for the consolidated analysis. Uploads, questions, retrieved text,
model output and drafts remain untrusted. [ADR 016](adr/016-consolidated-parallel-analysis.md)
records the human-approved architecture. Final migration/security verification is
pending the human's checks.

## Boundaries and controls

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
