# ADR 012 — Durable operational audit without payloads

- Status: accepted
- Date: 2026-09-22
- Plan: 15B.1

## Context

Phase 13B configured stdlib logging to stderr so `make run-api` shows HTTP envelopes,
use-case events and worker stages. Those lines vanish with the terminal. The only
durable operational table is `provider_call_accounting`, which stores provider,
model, `left_machine` and token counts — never prompt or completion text.

The next need is to answer "what happened, in which module, for which request"
after the process has restarted: rotating log files, one action row per user
command, one event row per internal stage, and HTTP plus provider envelopes in
PostgreSQL. The corpus is CVs and job applications. A second copy of that text in
a log table would be a privacy defect, not observability.

`docs/threat-model.md` listed audit logging as out of scope for the portfolio
build. That is no longer the decision.

Per-function enter/exit tracing was already rejected (AI log 111): it drowns
signal and risks document text in traces.

## Decision

Four sinks, one privacy contract. Stdlib logging and PostgreSQL; no logging
framework, no vendor APM, no request/response or model payloads.

1. **File-level process logs.** Keep the 13B stderr handler. Add an optional
   rotating `FileHandler` when `LOG_FILE` is set. Every `api/`, `application/`,
   `adapters/` and `ops/` module that performs I/O, mutation or orchestration
   uses `logging.getLogger(__name__)`. `domain/` stays silent.
2. **Action rows** in `workspace_actions`: one per user-initiated command at
   the use-case boundary (upload, delete, create role, ask, generate, provider
   change). Outcome, duration, entity ids, counts — never the document or
   question.
3. **Event rows** in `workspace_events`: worker stages, persistence mutations,
   batch counts. Optional `action_id`. Logger name is the emitting module.
4. **API envelopes.** HTTP `http_request_log` stores method, path, status,
   duration and sizes. Provider in/out extends `provider_call_accounting` with
   `correlation_id`, `success` and a safe `error_code`. Neither table stores a
   body, prompt, completion, cookie or `Authorization` header.

`format_fields` remains the only renderer for free-form fields. Attributes that
reach JSONB are ids, counts, durations, stage names and allowlisted codes.
Unknown event names do not become free text.

Recording is **fail-open**: a failure to insert an audit row is written to
stderr with safe fields and must not fail the user request. Audit inserts are
not allowed to roll back a successful CV or role write.

Hard delete of a workspace, CV, role or conversation removes matching action,
event and HTTP-envelope rows. Nothing soft-survives. There is **no**
`GET /api/logs` until authentication exists; operators read the host log file
and PostgreSQL.

Hermetic `create_app()` uses an in-memory recorder. Production uses a SQL
adapter behind the same port. Domain and application code still import no
FastAPI, SQLAlchemy or provider SDK.

## Consequences

- Operators can reconstruct a request's path through modules and stages without
  reconstituting the CV.
- Database backups and the audit tables contain metadata that a document was
  uploaded and that questions were asked, with timings. That is accepted
  metadata, not a copy of the documents.
- Fail-open can lose the trail during a database outage.
- Disk log files sit outside Postgres backup/restore and inherit the same field
  contract; they must not be pasted into tickets with personal data.
- A later authenticated log viewer is a new ADR. Shipping a read route now
  would expose audit metadata through the workspace cookie.

## Alternatives considered

- **Stderr only (leave 13B as-is).** Rejected: it cannot explain a failure after
  the terminal is gone, which is the reason for durable records.
- **Store request, response and model bodies "for debugging".** Rejected: that
  copies CVs, job descriptions and questions into a log table and breaks the
  threat model.
- **Log every function.** Rejected: noise and leak surface; 13B events plus
  actions and stages are the grain.
- **A logging framework or APM.** Rejected: stdlib plus PostgreSQL is enough
  for a local personal tool; a vendor sink is another egress path.
- **Retain audit rows after CV hard delete.** Rejected for this build: a trail
  that the document existed after the user asked to wipe it is a privacy
  choice the product does not take. Cascade with the workspace and its
  documents.
- **Public `GET /api/logs`.** Rejected until authentication exists.

Instruction and task order: [observability-logging-plan.md](../observability-logging-plan.md).
