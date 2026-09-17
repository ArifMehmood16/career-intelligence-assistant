# Engineering journal

One entry per phase checkpoint. Commands actually run and outcomes actually observed.
Nothing predicted, nothing rounded up.

## Template

```text
## Phase N — <name>

- Date:
- Commands run:
- Observed result:
- Decisions made:
- Problems hit and how they were resolved:
- Carried forward:
```

## Entries

## Phase 1 (partial) — run and deploy surface

- Date: 2026-09-17
- Commands run:
  - `uv venv --python 3.13 backend/.venv` and `uv pip install -e ".[dev]"`
  - `backend/.venv/bin/pytest tests/api/test_health.py --no-cov` **before** `main.py`
    existed
  - `make test`, `ruff check`, `ruff format --check`, `mypy`
  - `uv pip compile pyproject.toml [--extra dev] --no-header`
  - `make help`, `make -n config`, and a YAML parse of `compose.yaml`
- Observed result:
  - The liveness test failed on collection with no `career_assistant.main` — the
    intended red.
  - After `main.py`: 4 passed, 100% statement and branch coverage, coverage gate 80%
    satisfied.
  - ruff: "All checks passed", 12 files already formatted. mypy strict: "Success: no
    issues found in 10 source files".
  - Runtime lock 15 pins, dev lock 57 pins, both from Python 3.13.15.
  - `compose.yaml` parses to services db, api, web, ollama and volumes postgres_data,
    ollama_data.
- Decisions made:
  - Two dependency locks rather than one (AI_DEVELOPMENT_LOG 002).
  - Ollama behind a Compose profile rather than in the default stack (003).
  - Multi-stage images, both running as a non-root user, with health checks on the API
    and the web server. The sibling repository runs a dev server in its frontend image;
    this one builds and serves the Nitro output.
  - `alembic upgrade head` is deliberately absent from the backend image command and
    from `make run` until there is a schema, at phase 4.
- Problems hit and how they were resolved:
  - The workspace this was written from has no Docker and no bun, so neither image was
    built, the stack was never started, and `bunx tsc --noEmit`, `bun run lint` and the
    frontend build were not executed. Recorded as open on plan task 16.1 rather than
    asserted as working.
- Carried forward:
  - Build both images and run the stack. The two likeliest fixes are the Nitro preset
    and the `.output/server/index.mjs` path in `frontend/Dockerfile`.
  - Phase 0 is still open: threat model, synthetic fixtures, evaluation dataset shape.
  - Frontend hygiene (plan task 1.3) and frontend test tooling (1.4) are untouched.
