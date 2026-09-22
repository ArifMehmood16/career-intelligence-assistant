# Observability logging plan — files, actions, events, API envelopes

Instruction set for coding agents and the human reviewer. This is a **proposal**,
not an approved `PLAN.md` phase. Do not implement until the decisions in
[Human decisions required](#human-decisions-required) are answered.

**Related current work:** Phase 13D.6 completeness is still open. Phase 13B already
ships stderr operational logging. Phase 15 currently repeats none of 13B and still
lists audit logging as out of scope in `docs/threat-model.md`. This document would
become **Phase 15B** (working title) after approval, inserted after 13D's exit gate
unless the human explicitly overrides sequencing.

Read with: `AGENTS.md`, `PLAN.md` Phase 13B and Phase 15, `docs/threat-model.md`,
`backend/src/career_assistant/logconfig.py`,
`backend/src/career_assistant/application/providers/accounting.py`.

---

## Why this exists

The running API already prints INFO events to stderr (`request`, `cv.uploaded`,
worker stages). Those lines die with the terminal. There is no durable record of
what a workspace did, which HTTP call produced which analysis stage, or which
provider call sat on the critical path — except `provider_call_accounting`, which
stores identifiers and token counts only.

The product is a personal local tool that holds CVs. Observability must answer
"what happened, in which file, for which request" without becoming a second copy of
the documents.

---

## What already exists (do not rebuild)

| Layer | Where | What it does |
|---|---|---|
| Stderr events | Phase 13B, `logconfig.py` | Field-based INFO lines with `correlation_id` and `workspace_id` |
| HTTP envelope (console) | `RequestLoggingMiddleware` | method, path, status, duration_ms — **never the body** |
| Use-case events (console) | application services | `cv.uploaded`, `role.created`, Ask, generation |
| Persistence events (console) | SQL adapters | operation name + ids; SQLAlchemy `echo` off |
| Worker events (console) | analysis worker / pipeline | stages, counts, `incomplete_reasons` codes |
| Redaction | `RedactingFilter`, `format_fields` | drops multiline and over-long values; masks keys |
| Provider call accounting | `SqlCallAccountant` → `provider_call_accounting` | provider, model, `left_machine`, purpose, tokens, latency |

Known gap: `docs/threat-model.md` currently lists **audit logging** as out of
scope. This plan would reverse that for workspace-scoped operational records.

Already rejected (AI log **111**): a log statement in every backend function.
That drowns signal and risks document text in traces. This plan does **not**
reopen that.

**Partial coverage already shipped on the analysis path (2026-09-22):** stderr
events with `site=module.function` on failures (`log_failure`), safe `input=`
descriptors (ids/counts/stages only), claim batch diagnostics, and
`provider_call_accounting` for extract/assess/embed. Durable action/event/HTTP
tables and on-disk `LOG_FILE` are still this proposal — not implemented until
the human decisions below are answered.

---

## Goal

Four complementary records, one privacy contract.

1. **File-level process logs** — rotating log files on disk, one logger per
   Python module that already has a reason to speak, configurable level.
2. **Action-level records in PostgreSQL** — one row per user-initiated command
   (upload, delete, create role, ask, generate, change provider).
3. **Event-level records in PostgreSQL** — one row per internal stage that
   explains an action (worker claimed, claims batched, assessment incomplete).
4. **API in/out envelopes in PostgreSQL** — HTTP request/response metadata, and
   provider-call metadata, **never payloads**.

The model still extracts. The domain still decides. Logging does not score, map,
or phrase. Logging must not be able to reconstruct a CV, job description,
question, answer, prompt or embedding.

---

## Privacy contract (non-negotiable)

Copied from Phase 13B and tightened for durable storage.

**May record:** event name; logger name / module; entity ids; correlation id;
workspace id; HTTP method and path template; status code; contract error code;
byte/page/span/requirement/claim **counts**; durations; provider id; model tag;
`left_machine`; token counts; job stage names; boolean flags; file names of
**source modules**, not uploaded filenames-as-content.

**Must never record, in stderr, in log files, or in any database column
including JSONB:**

- document text, raw upload bytes, parsed spans, quotes
- questions, answers, draft bodies, prompts, embeddings, model completions
- request or response bodies, DTO dumps, cookies, `Authorization` headers
- API keys, database URLs with passwords, any secret
- SQL bound parameter values
- filenames when they might contain personal data (store `filename_length` and
  `media_type` only, or a hashed name if a name is operationally required)

`format_fields` remains the only renderer for free-form fields. A planted-phrase
test must fail if a CV/JD/question phrase appears in captured stderr, in the log
file, or in any audit table row.

Hard delete of a workspace, CV, role or conversation **must** delete the
matching action, event and HTTP-envelope rows. Logs must not soft-survive.
Provider-call accounting already cascades from `workspaces`; keep that.

---

## Interpretations (so the agent does not guess)

### File-level logging

Means **both**:

- **On-disk files:** a rotating `FileHandler` beside the existing stderr handler.
- **Per-module loggers:** `logging.getLogger(__name__)` in every `api/`,
  `application/`, `adapters/` and `ops/` module that performs I/O, mutation or
  orchestration.

Does **not** mean:

- enter/exit logs on every function
- `print` debugging
- a logging framework (structlog, loguru, Logstash, OpenTelemetry collector)
- domain-layer logging (`domain/` stays silent)

### Action-level logging

One durable row for a **user command** at the use-case boundary. Examples:
`cv.upload`, `cv.delete`, `cover_letter.upload`, `cover_letter.delete`,
`role.create`, `role.delete`, `role.reanalyse`, `ask.question`,
`generation.bullet`, `generation.pack`, `generation.letter`,
`settings.provider_changed`, `messages.delete`.

An action is started when the use case begins and finished when it returns or
fails. It carries `outcome` (`started` is not stored; store `succeeded` /
`failed` / `accepted` for 202 jobs) and `duration_ms`.

### Event-level logging

Internal facts that explain an action. Examples: `worker.claimed`,
`worker.stage`, `claims.batch`, `assessment.batch`, `sql.cv.insert`,
`provider.constructed`. Events optionally point at `action_id` and always at
`correlation_id`.

### API call in and out

Two envelopes, neither of which is a body dump:

| Direction | Store | Fields |
|---|---|---|
| Browser → FastAPI | new `http_request_log` | method, path, status, duration_ms, request_bytes (Content-Length), response_bytes when known, correlation_id, workspace_id, error_code |
| App → model provider | existing `provider_call_accounting`, extended | add `correlation_id`, `success`, `error_code`; keep tokens / latency / `left_machine`; still **no** prompt or completion text |

SSE streams: log the HTTP envelope once at close (final status + duration). Do
not persist token fragments. That matches the chat persistence rule.

---

## Architecture

Ports and adapters. No business logic in routes. Domain stays silent.

```text
HTTP middleware  →  record HTTP envelope  →  stderr + file + http_request_log
Use case         →  record action         →  stderr + file + workspace_actions
Adapter/worker   →  record event          →  stderr + file + workspace_events
AccountingCompletion/Embedding            →  provider_call_accounting
```

### New port

`application/ports/observability.py` (name may be `audit.py` if that is clearer):

```text
AuditRecorder
  record_action(action: ActionRecord) -> None
  record_event(event: EventRecord) -> None
  record_http(envelope: HttpEnvelope) -> None
```

Records are frozen dataclasses of ids, enums, counts and short codes only.
`metadata` if present is `Mapping[str, str | int | bool]` with the same
`format_fields` length/multiline rules applied **before** insert.

### Adapters

| Adapter | Used by | Behaviour |
|---|---|---|
| `InMemoryAuditRecorder` | `create_app()` hermetic tests | list in process; no database |
| `SqlAuditRecorder` | `create_production_app()` | insert then commit on its own short transaction, or the caller's UoW when already inside one |
| `NullAuditRecorder` | optional, only if a test must be silent | discard |

Stderr/file emission stays in `log_event`. The recorder is **additional**, not a
replacement. A single helper `emit(logger, event, recorder, ...)` that both logs
and records is allowed so call sites do not drift.

### Failure policy

Recording is **fail-open**. A database error while inserting an audit row must
be logged to stderr (safe fields only) and must **not** fail the user request.
Losing an audit row is better than failing a CV upload because the log table is
locked. Document this in the ADR.

Do **not** write audit rows on the same transaction as document insert if that
would roll back personal-data writes when logging fails — keep audit inserts
separate, or catch and swallow after the business commit.

### What stays out of `domain/`

Scoring, mapping, groundedness and intent routing do not import logging or the
recorder. Application services and adapters emit. That preserves the
architecture guard.

### No public read API in this phase

No `GET /api/logs`. There is no authentication yet. Operators read PostgreSQL
and the log file on the host. A UI log viewer is a later, authenticated feature
and is out of this plan.

---

## Schema (PostgreSQL, schema `career_assistant`)

Three new tables. Alembic migration. Models in
`adapters/persistence/models.py`. Indexes for `workspace_id`, `correlation_id`,
`created_at`.

### `workspace_actions`

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| workspace_id | uuid fk workspaces ON DELETE CASCADE | |
| correlation_id | text | from request context |
| action | varchar(64) | allowlisted names |
| entity_type | varchar(32) nullable | `cv`, `role`, `cover_letter`, `conversation`, `settings` |
| entity_id | uuid nullable | |
| outcome | varchar(16) | `succeeded`, `failed`, `accepted` |
| duration_ms | int | |
| error_code | varchar(64) nullable | contract code, never exception message text |
| actor | varchar(32) | `workspace` until auth exists |
| attributes | jsonb | counts and ids only; default `{}` |
| created_at | timestamptz | |

Check constraint: `action` and `outcome` in the allowlists.

### `workspace_events`

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| workspace_id | uuid fk CASCADE | nullable only for process-level events with no workspace yet (startup) |
| action_id | uuid fk workspace_actions ON DELETE SET NULL | optional parent |
| correlation_id | text | |
| logger_name | varchar(128) | `__name__` of the emitting module |
| event | varchar(64) | allowlisted |
| level | varchar(16) | `info`, `warning`, `error` |
| job_id / role_id / document_id | uuid nullable | sparse, not a kitchen-sink JSON |
| attributes | jsonb | counts, stages, provider ids |
| created_at | timestamptz | |

### `http_request_log`

| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| workspace_id | uuid fk CASCADE nullable | health has none |
| correlation_id | text | |
| method | varchar(8) | |
| path | varchar(256) | path **template** if cheap; otherwise path without query |
| query_id_keys | jsonb nullable | only known id query params (`roleId`, `version`); never free text |
| status | int | |
| duration_ms | int | |
| request_bytes | int nullable | from Content-Length |
| response_bytes | int nullable | from response Content-Length when set |
| error_code | varchar(64) nullable | |
| created_at | timestamptz | |

**Do not** add a `body` column. **Do not** store headers.

### `provider_call_accounting` extension

Add nullable `correlation_id text`, `success boolean not null default true`,
`error_code varchar(64)`. Backfill existing rows `success=true`. Still no
prompt, completion, or embedding text.

---

## File logging (process)

Extend `configure_logging` in `logconfig.py`. Stdlib only.

- Keep the stderr `StreamHandler` (13B).
- Add `RotatingFileHandler` when `LOG_FILE` is set and non-empty.
- Same `ContextFilter` and `RedactingFilter` on both handlers.
- Formatter includes `name` (module), level, message, correlation and workspace.
- Defaults: `LOG_LEVEL=INFO`, rotate at 10 MiB, keep 5 backups.
- `LOG_FILE` unset → files off (tests and default `make test`). Production and
  `make run-api` may set `LOG_FILE=var/log/career-assistant.log` or similar
  **outside the git tree**. Add `var/log/` to `.gitignore` if that path is used.
- `LOG_LEVEL=DEBUG` may be enabled locally. DEBUG still uses `format_fields`.
  DEBUG must not print request bodies. A test asserts a planted phrase is absent
  at DEBUG.

Settings live in a small `LoggingSettings` (or fields on existing settings) read
at construction. Domain does not read env. `main.py` already calls
`configure_logging`; extend that call.

Do not enable SQLAlchemy `echo`. `hide_parameters` stays true.

---

## Module coverage (file-level)

Every module below must have `_log = logging.getLogger(__name__)` and emit at
the listed moments. If a module already logs, **extend**, do not duplicate
noisily.

**API**

- `api/middleware.py` — HTTP envelope (exists); also `record_http`
- `api/errors.py` — contract error code (exists); attach to envelope
- route modules — no extra per-handler logs; middleware + use case cover them

**Application**

- documents, roles, ask, generation, analysis service — actions
- provider choice application path — action `settings.provider_changed`

**Adapters**

- persistence stores — events `sql.*` (mostly exist)
- analysis worker — events per stage (exist); persist them
- extraction / relatedness / provider factory — events with counts (exist)
- provider complete/embed adapters — do **not** log payloads; accounting covers
  in/out metadata

**Ops / main**

- startup already logs provider ids and db host:port; also write a
  `process.started` event with no secrets

**Silent**

- `domain/*`
- Pydantic schemas
- generated frontend `routeTree.gen.ts`

A unit test can scan `backend/src/career_assistant/{api,application,adapters}`
for modules that perform I/O (heuristic: import of ports, Session, httpx) and
lack `getLogger`. Keep that test conservative; do not fail on `__init__.py`.

---

## Event and action allowlists

Keep these in one module (`application/observability/names.py` or similar) so a
typo cannot insert free text as an event name.

**Actions:** `cv.upload`, `cv.delete`, `cover_letter.upload`,
`cover_letter.delete`, `role.create`, `role.delete`, `role.reanalyse`,
`ask.question`, `generation.bullet`, `generation.pack`, `generation.letter`,
`settings.provider_changed`, `messages.delete`.

**Events (initial set; extend only with a test):** existing 13B names
(`request`, `request_failed`, `http.error`, `cv.uploaded`, `cv.deleted`,
`cover_letter.deleted`, `role.created`, `role.deleted`, `worker.claimed`,
`sql.*`, `provider.constructed`, analysis stage names already in the worker).
Map current `log_event` names onto the allowlist rather than inventing a second
vocabulary.

Unknown names fail closed in tests; in production, log `event.unknown` with the
rejected name truncated to 64 chars of `[a-z0-9._]` and drop the rest.

---

## Sequencing vs PLAN.md

Default: **do not start this while 13D.6g is open.** Accuracy of evidence
assessment is the product priority. This work is observability.

If the human overrides, implement as Phase **15B** with tasks below, and add a
short pointer in `PLAN.md` under Phase 15. Do not tick 13D or 15.1–15.4 as a
side effect.

This is an architectural change: durable audit tables plus taking "audit
logging" out of the threat-model out-of-scope list. It needs an ADR
(`docs/adr/012-durable-operational-audit.md`) **before** the migration is
written.

---

## Human decisions required

Stop and wait if any of these is unanswered.

1. **Sequence.** Start after 13D.6g, or override and start now?
2. **Durable HTTP envelopes.** Approve storing method/path/status/duration in
   PostgreSQL (recommended), or files-only for HTTP?
3. **Bodies.** Confirm **no** request/response/prompt/completion bodies in the
   database. (Recommended: confirm. Storing bodies would copy CVs into a log
   table and break the threat model.)
4. **Read API.** Confirm **no** `GET /api/logs` until authentication exists.
5. **Retention.** Audit rows follow workspace/CV hard delete (recommended), or
   a separate longer retention? A longer retention after CV delete keeps a
   trail that the document existed; that is a privacy choice.
6. **Log file path.** Default `LOG_FILE` empty, document a `var/log/` example
   for `make run-api`?

Assumptions this plan proceeds with unless told otherwise: (1) after 13D.6g,
(2) yes durable HTTP envelopes, (3) no bodies, (4) no read API, (5) cascade
delete with the workspace/CV, (6) `LOG_FILE` optional.

---

## TDD delivery tasks

Work one task at a time. Red-green-refactor. Hermetic tests first; SQL tests
under `backend/tests/integration/`. Do not add a logging framework. Do not
change scoring, mapping or extraction behaviour.

### 15B.1 ADR and contract

- Write `docs/adr/012-durable-operational-audit.md`: purpose, privacy contract,
  fail-open, no read API, cascade delete, stdlib only, reuse `log_event`.
- Amend `docs/threat-model.md`: move audit logging from out-of-scope into a
  named control; add residual risk (DBA can read action metadata; bodies still
  absent).
- Tests: none yet.

### 15B.2 File handler and level

- Failing tests in `backend/tests/unit/test_logconfig.py` (new) or extend
  `test_operational_logging.py`:
  - when `LOG_FILE` points at a temp path, an emitted event is in the file
  - planted CV phrase and planted key are absent from the file even at DEBUG
  - multiline and over-long fields still redact
  - when `LOG_FILE` is empty, no file handler is attached
- Implement in `logconfig.py` + settings.
- `make run-api` documentation in README: optional `LOG_FILE`, unbuffered
  stderr unchanged.

### 15B.3 Recorder port and in-memory adapter

- Failing unit test: recording an action with a planted phrase in `attributes`
  raises or redacts **before** store; the in-memory list never contains the
  phrase.
- Implement dataclasses, allowlists, `InMemoryAuditRecorder`, redaction at the
  boundary.
- Architecture guard still forbids FastAPI/SQLAlchemy in `application/`.

### 15B.4 HTTP envelope → recorder + stderr

- Extend `test_operational_logging.py`: health request records one envelope
  with method, path, status, correlation id; planted header values that look
  like secrets do not appear.
- Validation error still logs `code=` not the body, **and** persists
  `error_code` on the envelope.
- Wire middleware to `app.state.audit_recorder`. Hermetic `create_app()` uses
  in-memory.

### 15B.5 Actions at use-case boundaries

- API tests: CV upload records `cv.upload` succeeded with `document_id` and
  counts, not text. Role create records `role.create` accepted (202) with
  `role_id` / `job_id`. Delete records `cv.delete`. Ask records `ask.question`
  without the question text. Provider change records `settings.provider_changed`
  with provider ids only.
- Failed admit (too large, wrong type) records `failed` + contract `error_code`.
- Keep existing `log_event` names working so 13B tests stay green.

### 15B.6 Events from worker and persistence

- Unit/API: a hermetic analysis run records `worker.claimed` and stage events
  with job/role ids and counts, never requirement text.
- Claim-batch and assessment-batch events already on stderr gain a durable
  event row.
- `sql.*` events remain; persist the ones that mutate.

### 15B.7 SQL adapter, migration, provider accounting columns

- Integration tests against PostgreSQL:
  - insert action + event + http envelope; read back
  - planted phrase absent from `attributes` jsonb
  - CV hard delete removes that workspace's actions, events, http rows (or
    workspace delete cascades — pick one and test it)
  - conversation hard delete removes ask-related rows for that conversation id
    if they were keyed that way; otherwise workspace cascade is the tested path
  - provider call row stores `correlation_id` and `success`
- Alembic migration in `backend/migrations/versions/`.
- `SqlAuditRecorder` + models + UoW repository. Production wiring in
  `create_production_app` / `build_sql_stores`.
- Integration cleanup in `conftest.py` must truncate the new tables.

### 15B.8 Provider in/out without payloads

- Unit test on `AccountingCompletion`: a complete() records tokens, latency,
  `left_machine`, purpose, correlation id; the stored metadata has no
  `request.user` / completion text.
- Failure path: provider timeout records `success=false` and a safe
  `error_code` (`provider_timeout`), still no body.
- Do not log httpx request text in provider adapters.

### 15B.9 Module logger presence and redaction regression

- Conservative test that application/adapter modules with I/O have a logger.
- Re-run 13B.6 planted-phrase and planted-key tests against stderr **and**
  file **and** in-memory recorder.
- `make lint` on touched Python. Focused pytest then hermetic `make test`.

### 15B.10 Documentation

- `README.md`: `LOG_FILE`, what operators will see, what is in Postgres.
- `docs/production-wiring.md`: who writes the three tables; no read route.
- `docs/engineering-journal.md` checkpoint with commands actually run.
- `PLAN.md` Phase 15B tasks ticked only after evidence.
- Factual `AI_DEVELOPMENT_LOG.md` entry.

**Exit gate:** focused redaction tests pass on stderr, file and SQL;
integration hard-delete removes audit rows; hermetic suite green; no document
text in any of the three sinks; ADR 012 accepted; threat model updated.

---

## Expected files (implementation, after approval)

| File | Purpose |
|---|---|
| `docs/adr/012-durable-operational-audit.md` | decision |
| `docs/threat-model.md` | audit in scope |
| `backend/src/career_assistant/logconfig.py` | file handler, shared emit |
| `backend/src/career_assistant/settings.py` | `LOG_FILE`, `LOG_LEVEL` |
| `config/app.env` | commented examples, no secrets |
| `backend/src/career_assistant/application/ports/observability.py` | port + records |
| `backend/src/career_assistant/application/observability/` | allowlists, redaction-before-store |
| `backend/src/career_assistant/adapters/persistence/models.py` | three tables + accounting columns |
| `backend/src/career_assistant/adapters/persistence/audit.py` | `SqlAuditRecorder` |
| `backend/src/career_assistant/adapters/persistence/unit_of_work.py` | repository |
| `backend/migrations/versions/*_operational_audit.py` | Alembic |
| `backend/src/career_assistant/api/middleware.py` | persist envelope |
| `backend/src/career_assistant/main.py` | wire recorder |
| `backend/src/career_assistant/application/providers/accounting.py` | correlation + success |
| application services / worker | `record_action` / `record_event` at existing `log_event` sites |
| `backend/tests/api/test_operational_logging.py` | extend |
| `backend/tests/unit/test_audit_recorder.py` | new |
| `backend/tests/integration/test_audit_persistence.py` | new |
| `README.md`, `docs/production-wiring.md`, `PLAN.md` | after evidence |

Do not reformat the repository. Do not touch frontend except if a future
authenticated viewer is separately approved (not this plan).

---

## Agent working protocol for this plan

1. Read `AGENTS.md`, `README.md`, `PLAN.md`, `AI_DEVELOPMENT_LOG.md`, this file.
2. Confirm the human decisions above are answered.
3. Implement **one** 15B.n task.
4. Write the smallest failing test first; observe the failure.
5. Implement the minimum to pass.
6. Run the focused test, then related 13B logging tests.
7. Inspect the diff for bodies, secrets, domain imports, unrelated files.
8. Stop and report with the AGENTS.md task report. Do not start 15B.n+1.

Suggested branch after approval: `feat/phase-15b-durable-operational-audit`.

---

## Security and quality review checklist (every task)

- Planted CV/JD/question phrase absent from stderr, file and DB.
- Planted API key absent from all three.
- No `echo=True` on the engine.
- No exception handler logging `str(exc)` if the parse error might include a
  document snippet — log `type(exc).__name__` and a code.
- JSONB `attributes` keys allowlisted or prefix-checked (`count_`, `id_`,
  `ms_`, `stage_`, `provider_`).
- Hard delete / `ON DELETE CASCADE` covered by an integration test.
- Fail-open does not swallow programming errors in the use case itself — only
  recorder failures.

---

## Residual risks (to record in the threat model)

- A host or database compromise exposes **that** a workspace uploaded a CV and
  asked questions, with timings. It does not expose the CV if the contract holds.
- Fail-open can lose the audit trail during a DB outage.
- DEBUG on a misconfigured handler that bypasses `format_fields` could leak
  text; the redaction tests are the control.
- Disk log files are outside Postgres backup/restore; operators must not copy
  them into tickets with personal data. Files inherit the same field contract.
- No authentication: anyone with the workspace cookie can generate actions.
  That is already true of the product; audit tables do not make it worse, and
  must not be world-readable over HTTP.

---

## Explicitly not in this plan

- Per-function tracing, decorators on every method, OpenTelemetry spans
- Vendor APM, Sentry, Datadog
- Request/response body capture "for debugging"
- Frontend console logging of document text
- A logs UI
- Changing analysis, scoring, or extraction
- Soft-deleted audit rows
- SQLite or filesystem as a persistence fallback for audit tables
