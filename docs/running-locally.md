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
make test-evaluation   # offline quality baseline on the labelled fixtures
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

`make run` never starts a database container. It uses `DATABASE_URL` from
`config/app.env` and defaults to a developer-managed PostgreSQL on
`localhost:5432`. `make db-create` (also run by `make db-migrate` / `make run`)
creates the `DATABASE_URL` and `TEST_DATABASE_URL` databases when they are missing;
the role in those URLs must already exist and be allowed to `CREATE DATABASE`.
Application tables live in the dedicated Postgres schema `career_assistant` (not
`public`); Alembic creates that schema and owns the table set. `make run-docker`
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
