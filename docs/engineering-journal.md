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

## Phase 1 — Skeleton and quality gates (remainder)

- Date: 2026-09-18
- Commands run:
  - `bunx tsc --noEmit` — passed on Lovable sources as delivered.
  - `bun run lint` — failed as delivered with 226 Prettier errors; after
    `bun run format`, lint passed with 2 pre-existing react-refresh warnings only.
  - `bunx vitest run` — StatusMark component tests and ESLint guard tests green.
  - `make lint` and `make test` after wiring frontend into the Make targets.
- Observed result:
  - Deleted `frontend/package-lock.json` and empty `src/app/` stubs; ignored
    `.output` / `.wrangler` build artefacts.
  - Vitest + Testing Library + jsdom added; first test covers `StatusMark` from props.
  - Custom ESLint plugin bans hex / raw Tailwind palette classes in
    `src/components/**`; fixture imports banned outside tests (exceptions:
    `api/client.ts`, `api/fixtures.ts`, `routes/dev.states.tsx`).
  - GitHub Actions workflow `.github/workflows/ci.yml` runs install, `make lint`,
    `make test` on Python 3.14 and Bun 1.4.0.
- Decisions made:
  - Keep temporary fixture imports in `api/client.ts` until Phase 12 replaces the
    fixture store; the guard still blocks components and routes.
  - Format the as-delivered Lovable tree so the Phase 1 exit gate can pass; record
    the Prettier failure as the only as-delivered defect.
- Problems hit and how they were resolved:
  - ESLint `lintText` guards initially pointed at `src/` instead of the frontend
    root; fixed the test path resolution.
- Carried forward:
  - Phase 2 model providers.
  - Phase 16.1 still needs a real Docker/bun image build verification.

## Phase 0 — Repository baseline and decisions

- Date: 2026-09-18
- Commands run:
  - `backend/.venv/bin/pytest tests/unit/test_phase0_baseline.py -q --no-cov`
    observed failing on missing Product scope, threat-model draft coverage, fixtures,
    dataset stub and scoring rubric config (intended red).
  - Same command after the Phase 0 assets landed — all Phase 0 baseline tests passed.
  - `backend/.venv/bin/pytest -q` (full hermetic suite) after the green cycle.
- Observed result:
  - AGENTS.md now carries a Product scope section aligned with features.md
    “Deliberately not features”, and hard delete explicitly includes generated drafts.
  - ADRs 001–007 confirmed accepted and dated 2026-09-18; contents match PLAN fixed
    direction (monolith, Postgres/pgvector, pluggable providers + egress, deterministic
    scoring, runtime provider selection, TanStack Start, grounded generation).
  - threat-model.md names upload, document/job-description text, model output,
    generated drafts, personal data and egress controls.
  - Fixtures: 3 synthetic CVs, 6 synthetic JDs, manifest pairings for clean / partial /
    poor / vague seniority / injection / recency decay.
  - `sample-data/evaluation/dataset.json` stub with the documented case shape.
  - Starting rubric weights in `config/scoring_rubric.toml`, referenced from features.md.
- Decisions made:
  - Scope boundaries stay as features.md states; no product expansion in Phase 0.
  - Rubric constants are configuration from day one, not deferred until scoring code.
- Problems hit and how they were resolved:
  - Host Python was already on 3.14 from the preceding commit; Phase 0 tests run on that
    interpreter.
- Carried forward:
  - Phase 1 remaining: frontend hygiene (1.3), Vitest (1.4), colour/fixture ESLint guard
    (1.8), CI (1.9).

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
