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

### 004 — Backend Python bumped to 3.14

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

### 005 — Phase 0 repository baseline

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

### 006 — Phase 1 frontend quality gates

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

### 007 — Phase 2 model providers

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 2.1–2.12
- Prompt intent: continue with the next phase (model providers) through completion.
- Suggestion: ports + capability descriptors; hermetic/Ollama/OpenAI/Anthropic
  adapters behind an egress gate; shared contract suite on recorded HTTP fixtures;
  resilience, accounting, key redaction, explicit fallback.
- Outcome: accepted.
- Reason: matches ADR 003/005; keeps default runs hermetic; no vendor SDK lock-in.
- Human validation: `pytest` hermetic suite green (coverage ≥80%), ruff and mypy
  clean on the package.

### 008 — Remove Lovable branding and telemetry from the frontend

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: Phase 2 PR follow-up (branding)
- Prompt intent: strip Lovable mentions, logo, favicon and trackers; brand as CIA.
- Suggestion: delete lovable error-reporting hook, replace favicon with an original
  CIA monogram SVG, update shell/docs titles, keep `@lovable.dev/vite-tanstack-config`
  only as the existing Vite/Start build helper.
- Outcome: accepted.
- Reason: product branding should not ship editor telemetry or vendor marketing.
- Human validation: `bun run test` (6 passed), `bun run lint` (warnings only),
  `bun run typecheck` green.

### 009 — Phase 3 document intake and spans (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 3.1–3.7
- Prompt intent: continue Phase 3 following TDD where possible.
- Suggestion: commit failing intake tests first; implement admit → extract → span
  pipeline for plain text, PDF and DOCX; span resolution and normalisation.
- Outcome: accepted.
- Reason: exit gate requires fixture CV → spans round-trip and safe rejection of
  bad uploads; tests encode that before parsers land.
- Human validation: intake tests red then green; full hermetic pytest, ruff, mypy
  observed green.

### 010 — PostgreSQL persistence design review

- Date: 2026-09-18
- Tool / model: Codex
- Plan task: Unplanned design review before Phase 4
- Prompt intent: inspect the remaining plan for gaps and make PostgreSQL the explicit
  source of truth for uploaded CVs and cover letters, questions and answers, with a
  local database for Make and a container database for Compose/deployment.
- Suggestion: expand Phase 4 onward with bounded original-file storage, conversation
  and citation tables, transaction/idempotency rules, local/test database separation,
  container persistence and backup/restore; amend the controlling ADR, API contract,
  feature specification and threat model.
- Outcome: changed
- Reason: uploaded cover letters are stored and queryable as requested, but are
  deliberately excluded from candidate claims and fit scoring because self-authored
  prose is not independent evidence. Generated letters remain provenance-bearing
  drafts linked to cited CV spans.
- Human validation: pending review of the documentation diff. Automated consistency
  checks and existing quality gates are recorded in the task report.

### 011 — Phase 4 PostgreSQL persistence (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 4.1–4.13
- Prompt intent: continue with the next incomplete PLAN work (Phase 4 persistence).
- Suggestion: red tests for DatabaseSettings and the adapter boundary; then SQLAlchemy
  models, Alembic baseline, repository unit-of-work, integration suite, and Make
  db-check/db-migrate targets.
- Outcome: accepted.
- Reason: exit gate requires migrations and scoped document/conversation round-trips
  on real PostgreSQL with no production SQLite/memory fallback.
- Human validation: hermetic pytest (~82% coverage), ruff, mypy green; eight
  integration tests green against local pgvector; `make db-check` and `make db-migrate`
  observed green.

### 012 — Dedicated PostgreSQL application schema

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: follow-up to Phase 4 (persistence)
- Prompt intent: stop using the public schema; use a dedicated schema.
- Suggestion: `career_assistant` schema, MetaData.schema, search_path, forward
  migration moving tables out of public; keep `vector` in public.
- Outcome: accepted.
- Human validation: unit + integration tests green; `\dt career_assistant.*` shows
  21 tables; `make db-migrate` / `make db-check` green.

### 013 — Phase 5 requirement extraction (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 5.1–5.7
- Prompt intent: continue with the next phase (requirement extraction).
- Suggestion: domain Requirement; rules extractor for bulleted JD sections; span
  validation; injection and vague fixtures; cover-letter rejection; model-backed path
  intersecting CompletionPort JSON with rule spans.
- Outcome: accepted.
- Reason: exit gate requires six fixture JDs with resolvable spans and no injection
  leakage; rules stay default so hermetic runs need no network.
- Human validation: eight focused extraction tests green; hermetic pytest (~81%),
  ruff, mypy green.

### 014 — Phase 6 evidence / claim extraction (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 6.1–6.5
- Prompt intent: continue with Phase 6 evidence extraction.
- Suggestion: domain Claim; pure date-derived recency/duration; rules CV extractor;
  span validation; cover-letter rejection; model-backed path intersecting hermetic
  claims JSON with rule spans.
- Outcome: accepted.
- Reason: exit gate requires fixture CVs with resolvable spans and dated-experience
  recency that is not assumed recent.
- Human validation: eight focused claim tests green; hermetic pytest, ruff, mypy.

### 015 — Phase 7 mapping and scoring (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 7.1–7.6
- Prompt intent: continue with the next phase (mapping and scoring) under TDD.
- Suggestion: pure `domain/mapping.py` policy with reason codes; similarity as
  candidate hint only; `domain/scoring.py` + `application/scoring/rubric_loader`
  reading `config/scoring_rubric.toml`; property and counterfactual tests; fixture
  CV×JD exit-gate test with no model call.
- Outcome: accepted.
- Reason: exit gate requires a stable explained score and deltas without a model;
  the invariant keeps judgement in domain arithmetic, not the LLM.
- Human validation: nine focused mapping/scoring tests green; hermetic pytest
  (~84%), ruff, mypy green.

### 016 — Phase 8 analysis jobs (TDD, red commits first)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 8.1–8.7
- Prompt intent: continue Phase 8 with team TDD — test commits before
  implementation.
- Suggestion: domain job lifecycle; `AnalysisService` orchestration with fakes;
  Alembic job/role columns; SQL role/job/analysis repos; transactional publish and
  fail discard; CV-replace reanalysis enqueue.
- Outcome: accepted.
- Reason: exit gate needs immediate enqueue, ready-on-success, failed-with-no-
  partials; Postgres is the system of record for jobs.
- Human validation: unit domain + pipeline green; integration persistence green
  (`-m integration`); hermetic pytest (~84%), ruff, mypy green.
- Process note: standing instruction — for future work, commit failing tests
  before implementation commits; assume concurrent teammates.

### 017 — Phase 9 ask domain (TDD, partial)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 9.1–9.6, 9.10 (9.7–9.9 deferred)
- Prompt intent: continue with TDD-style development on the next phase.
- Suggestion: intent router; structured mapping answers + citation validation;
  open-question retrieval rules and untrusted prompt budgets — each as red then
  green commits.
- Outcome: accepted for the domain slice; streaming/persistence left open.
- Reason: structured intents must not use vector search; citations must resolve
  or become insufficient before any HTTP surface exists.
- Human validation: focused unit suites green; hermetic pytest (~84%), ruff, mypy.

### 018 — Phase 9 ask streaming and persistence (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 9.7–9.9
- Prompt intent: continue next work with TDD after PR #17 merged to main.
- Suggestion: `AskService` with shared stream/non-stream path; in-memory red specs
  then green; conversation repo lookup/history/citations red integration then green.
- Outcome: accepted.
- Reason: exit gate needs stream parity, question-before-answer persistence, and
  idempotent clientRequestId without storing partial tokens.
- Human validation: unit ask use-case green; integration ask persistence green;
  full `-m integration` green; hermetic pytest (~84%), ruff, mypy.

### 019 — Phase 10 grounded generation (TDD, 10.9 deferred)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 10.1–10.8
- Prompt intent: continue with TDD after Phase 9 persistence merged to main.
- Suggestion: groundedness validator; gap plan; generate_draft pipeline with
  counters; hermetic bullets; cover letter refuse; interview pack; markdown export
  — red commits before each green slice.
- Outcome: accepted for generation behaviour; 10.9 store deferred.
- Reason: ADR 007 requires fail-closed validation before any draft reaches a user;
  hermetic templates keep the feature model-free.
- Human validation: focused unit suites green; hermetic pytest (~84%), ruff, mypy.
