# Running locally

| Path | You need | First commands |
|---|---|---|
| Make | Python 3.14, bun, local PostgreSQL 16 with pgvector on port 5432, Ollama | `make setup` then `make run` |
| Docker | Docker Engine and Compose v2 | `make run-docker` — written but not yet verified end to end (PLAN 16.1) |

The running product needs the two local models:

```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

```bash
make setup             # config/app.env, Python venv from the lock, bun install
make test              # hermetic backend and frontend tests — no database, key or model
make lint              # ruff, mypy strict, tsc, eslint
make typecheck         # mypy and tsc only
make test-integration  # PostgreSQL/pgvector tests against TEST_DATABASE_URL
make run               # migrate, then API and web in two Terminal windows (macOS)
make run-api           # API only — application events and uvicorn logs here
make run-web           # web only — Vite logs here
make help              # every target, with what it needs
```

```bash
make run-docker   # copies config/app.env, builds and starts db, api and web
# Web http://localhost:3000   API http://localhost:8000/docs
make down         # stop it again
```

All workspaces use the chunk/search/judge analysis. The pipeline selector and
`PIPELINE_VERSION` have been removed. Configure per-model context, output and
concurrency in `config/models.toml`; restart after editing model configuration.
`ANALYSIS_MAX_CONCURRENT_JOBS` bounds overlapping role jobs; `HOSTED_MAX_IN_FLIGHT`
bounds hosted calls. `PARSING_WORKERS` and `PARSING_TIMEOUT_SECONDS` configure the
separate spawned PDF/DOCX parser pool. Plain text avoids process startup.

The retired v1 evaluation command has been removed. `make benchmark` implements
current cold/warm application timing with synthetic fixture retrieval; it defaults
offline and needs no database or key. `BENCHMARK_ARGS` passes named cases, repeat
count, report destination or explicit live-provider selections. Execution is still
deferred. See [measurement scope and commands](evaluation.md#current-analysis-benchmark-plan-194).
Frozen-label quality evaluation remains open in PLAN 19.4.

The new forward migrations add call-progress fields and retire legacy derived
analysis storage. They preserve original uploads and current chunk/verdict results;
old analyses must be rerun. A user-reported attempt to run the retirement revision
failed because a check-constraint name was prefixed twice. The revision now uses
Alembic `op.f()` for complete names in both directions. This code repair has not been
executed by the agent; the human may retry `make db-migrate`. Disposable PostgreSQL
preservation checks and final verification remain pending; a successful personal
migration is not claimed.

`make run` never starts a database container. It uses `DATABASE_URL` from
`config/app.env` and defaults to a developer-managed PostgreSQL on
`localhost:5432`. `make db-create` (also run by `make db-migrate` / `make run`)
creates the `DATABASE_URL` and `TEST_DATABASE_URL` databases when they are missing;
the role in those URLs must already exist and be allowed to `CREATE DATABASE`.
Application tables live in the dedicated Postgres schema `career_assistant` (not
`public`); Alembic creates that schema and owns the table set. pgvector lives in an
`extensions` schema, where Supabase keeps it. `make db-migrate` creates that schema
and moves pgvector into it (PLAN 18.3); nothing needs running by hand when the
migrations installed pgvector, because the role in `DATABASE_URL` then owns it. Only
if pgvector was installed by a different role — for example `CREATE EXTENSION vector`
run as `postgres` — does the migration stop with `must be owner of extension vector`;
then have a superuser run `CREATE SCHEMA IF NOT EXISTS extensions; ALTER EXTENSION
vector SET SCHEMA extensions;` once, and run `make db-migrate` again. Every
application table has row-level security enabled with no policies: the owning role
is unaffected, and any other role reads nothing. `make run-docker`
instead starts the Compose `db` container; the API reaches it privately as
`db:5432`, while development Compose exposes host port 5433 to avoid colliding
with the local instance. Both paths use the same Alembic migrations and PostgreSQL
repositories. SQLite and filesystem-backed uploads are not fallbacks. Which store
each route uses is listed in [docs/production-wiring.md](production-wiring.md).

In Compose, Ollama sits behind a profile so a default `up` downloads no model:

```bash
docker compose --env-file config/app.env --profile ollama up -d
```

PostgreSQL stores the bounded original bytes for CVs, job descriptions and supporting
cover letters alongside parsed text and spans. Uploaded cover letters may be queried
and cited. Generated cover letters and final cited chat answers are persisted with
provenance; partial streamed tokens are not stored as answers. Role analysis is an
in-process worker over queued PostgreSQL jobs: HTTP returns `202` with `analysing`
before extraction finishes, and a process restart recovers queued and stale-running
work. A failed reanalysis keeps the last valid analysis visible.

## Observability

When an analysis fails, the status endpoint can still return HTTP 200: inspect the
job's `state` and `error`. A preceding OpenAI `provider.request_failed` event now
identifies completion/embedding/tool calling, configured model, HTTP status and a
fixed error category. It retains only allowlisted vendor codes and parameter names,
never the vendor message or body. `request_format_rejected` with
`parameter=response_format` identifies a rejected structured response format.

The 2026-10-02 advert-schema repair preserves empty arrays rather than forcing
nullable types into optional nested collections. After updating, restart the API
or let its development reloader finish, then start a new analysis. A failed job
does not resume after an account or code fix. Synthetic request acceptance was
observed; complete analysis and regression verification remain pending.

- `make run-api` writes INFO events to stderr (`request`, `cv.uploaded`,
  `role.created`, worker stages, batch diagnostics). Lines carry ids, counts,
  durations and safe error codes — never document text, questions, answers, prompts
  or API keys. `PYTHONUNBUFFERED=1` is set so the lines are not stuck in a buffer.
- Set `LOG_FILE` (for example `var/log/career-assistant.log`) to also write a rotating
  file with the same field contract; leave it empty for stderr only.
- `provider_call_accounting` in PostgreSQL records every extraction, assessment,
  embedding and answer call: provider, model, purpose, tokens, latency and whether
  content left the machine.
- Action, event and HTTP-envelope audit records follow
  [ADR 012](adr/012-durable-operational-audit.md). They are held in memory today
  and become PostgreSQL tables in PLAN 15B.7. There is no log-read API.
