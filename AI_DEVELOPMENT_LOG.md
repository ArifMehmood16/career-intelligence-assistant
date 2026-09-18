# AI Development Log

A factual record of how AI coding tools were used on this project. One entry per
meaningful agent-assisted change. Entries are drafted by the agent and approved by
the developer before commit.

Record what was **accepted**, what was **changed**, and what was **rejected**. The
rejections are the most valuable entries: they show the judgement applied on top of
the tool.

Never record a command output, metric, date or commit hash that was not observed.

## Entry template

```text
### NNN — <short title>

- Date:
- Tool / model:
- Plan task:
- Prompt intent: (what was asked, not the full prompt)
- Suggestion: (what the tool proposed)
- Outcome: accepted | changed | rejected
- Reason: (why — the human-owned decision)
- Human validation: (tests run, diff reviewed, docs checked)
```

## Entries

### 001 — Run and deploy surface brought forward

- Date: 2026-09-17
- Tool / model: Claude (Opus 5), agent session
- Plan task: 1.1, 1.2, 1.5, 1.6, 1.7, part of 16.1 — taken out of order at the
  developer's direction, before Phase 0 is closed.
- Prompt intent: build the Docker and Make run/deploy setup, patterned on the sibling
  repository `task-code-repository-rag`.
- Suggestion: mirror the sibling's `Makefile`, `compose.yaml` and Dockerfiles, and add
  the minimum backend needed for the stack to actually start.
- Outcome: accepted, with three changes recorded below.
- Reason: a Compose file that builds an image with nothing to run is a prop. The
  smallest honest version of "it runs" is a liveness endpoint, so Phase 1's first
  red-green cycle came with it.
- Human validation: pytest 4 passed with 100% coverage; ruff check and format clean;
  mypy strict clean on 10 source files; `make help` and `make -n config` parse;
  `compose.yaml` parses and every variable it interpolates exists in
  `config/app.env.example`. Docker was not available on this machine, so **no image
  was built and the stack was never started** — 16.1 stays open.

### 002 — Single dependency lock split into runtime and dev

- Date: 2026-09-17
- Tool / model: Claude (Opus 5), agent session
- Plan task: 1.1
- Prompt intent: match the sibling repository's dependency handling.
- Suggestion: one `requirements.lock` containing runtime and development pins, as the
  sibling does, installed by both `make setup` and the container image.
- Outcome: changed.
- Reason: that ships pytest, bandit, mypy and pip-audit — 57 pins — into the runtime
  image, where they are attack surface that runs as the API user and never gets used.
  Split into `requirements.lock` (15 runtime pins, what the image installs) and
  `requirements-dev.lock` (what `make setup` installs). `make security` audits both.
- Human validation: both locks regenerated with `uv pip compile` against Python
  3.13.15 and diffed; the backend image copies only the runtime lock.

### 003 — Rejected: unpinned dependency ranges and an Ollama service in the default stack

- Date: 2026-09-17
- Tool / model: Claude (Opus 5), agent session
- Plan task: 1.1, 16.1
- Prompt intent: as above.
- Suggestion: (a) install from `pyproject.toml` ranges in the image rather than a lock;
  (b) include the `ollama` service in the default Compose stack, as the sibling does.
- Outcome: rejected.
- Reason: (a) an image that resolves versions at build time is not the image that was
  tested; the lock is the point. (b) The default providers are hermetic, so a default
  `up` that pulls a multi-gigabyte Ollama image contradicts the product's own claim
  that a reviewer can clone and run with no model download. Ollama moved behind a
  Compose profile and is started only when asked for.
- Human validation: `docker compose --profile ollama` documented in `compose.yaml`,
  the README quick start and `make help`.

### 002 — Backend Python bumped to 3.14

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: unplanned — unblock `make setup` after host Python mismatch
- Prompt intent: upgrade the project to the most recent Python on the system
  (3.14.4) instead of installing 3.13.
- Suggestion: widen `requires-python` to include 3.14; bump Docker, ruff, mypy,
  README/PLAN/Makefile; add ADR 008; recreate the venv and re-run setup.
- Outcome: accepted.
- Reason: developer chose to track system Python 3.14 rather than maintain a
  separate 3.13 toolchain. The previous upper bound `<3.14` was the direct cause
  of the setup failure.
- Human validation: `make setup` succeeded on Python 3.14.4;
  `backend/.venv/bin/python --version` reports 3.14.4; `import career_assistant`
  succeeds. Regenerated stale `frontend/bun.lock` so the frozen install step
  could pass.

### 003 — Phase 0 repository baseline

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 0.1–0.6 (Phase 0 exit gate)
- Prompt intent: complete Phase 0 with TDD-style commits, then open a PR.
- Suggestion: failing hermetic baseline tests first; then AGENTS product scope,
  threat-model draft/personal-data coverage, synthetic fixtures, evaluation stub,
  scoring rubric config, ADR date confirmation, PLAN/journal updates.
- Outcome: accepted.
- Reason: Phase 0 requires decisions and fixtures before application behaviour;
  pinning those with tests keeps the exit gate enforceable.
- Human validation: focused `pytest tests/unit/test_phase0_baseline.py --no-cov`
  observed red then green; full hermetic `pytest` passed with 100% package coverage
  on the existing skeleton.

### 004 — Phase 1 frontend quality gates

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 1.3, 1.4, 1.8, 1.9
- Prompt intent: continue with the next phase through completion and PR.
- Suggestion: frontend hygiene, Vitest/Testing Library, ESLint design/fixture
  guards with red-green proof, Makefile typecheck/test wiring, GitHub Actions CI.
- Outcome: accepted.
- Reason: Phase 1 exit gate requires lint, typecheck and hermetic tests on both
  halves; Lovable as delivered failed Prettier-only lint until formatted.
- Human validation: `bunx vitest run` (5 passed, including red-then-green ESLint
  guards), `make typecheck`, `make lint`, and `make test` all observed green.
