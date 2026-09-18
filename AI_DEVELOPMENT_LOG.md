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

### 020 — Phase 10.9 artefact persistence (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 10.9
- Prompt intent: continue after Phase 10.1–10.8 merge; finish artefact store.
- Suggestion: red integration specs for save/versioning/reject-FAIL; migration for
  version + groundedness provenance; `DraftRepository` + `SqlDraftRepository` on UoW.
- Outcome: accepted.
- Reason: only PASS (or template-fallback that still passes validation) content may
  persist; regenerations must be immutable versions, not in-place updates.
- Human validation: draft persistence integration green; full `-m integration` green;
  hermetic pytest (~84%), ruff, mypy.

### 021 — Phase 11 API wire foundation (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.1, 11.2, 11.4, 11.5, 11.6
- Prompt intent: continue on updated main with TDD; start Phase 11 API contracts.
- Suggestion: shared camelCase `ApiModel`; workspace cookie middleware; correlation
  id middleware; safe error envelope; `/api/ready` with injectable probe (SQL probe
  kept under adapters/persistence).
- Outcome: accepted for the HTTP foundation; 11.3 upload limits and feature routes
  deferred to follow-up slices.
- Reason: every later route needs aliases, workspace identity, correlation ids and
  safe errors before CV/role handlers land.
- Human validation: focused API suites green; hermetic pytest (~83%), ruff, mypy;
  persistence boundary test green after moving SettingsReadiness into adapters.

### 022 — Phase 11.3 upload limit and 11.7 providers (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.3, 11.7
- Prompt intent: continue on updated main after PR #21; keep TDD.
- Suggestion: pure ASGI Content-Length gate; provider catalogue + choice routes with
  server-side egress acknowledgement; redaction assertion for API keys.
- Outcome: accepted; durable SQL provider_settings deferred.
- Reason: pre-buffer rejection is the contract requirement; hosted confirmation must
  not be UI-only.
- Human validation: API upload + provider suites green; hermetic pytest (~83%),
  ruff, mypy.

### 023 — Phase 11.8 partial CV/span/role/job routes (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial)
- Prompt intent: continue on updated main with TDD after PR #22.
- Suggestion: CV paste lifecycle; span Evidence with spanId; roles requiring CV and
  returning queued jobs — hermetic in-memory stores first.
- Outcome: accepted as a contract slice; SQL persistence and remaining 11.8 artefacts
  deferred.
- Reason: prove workspace-scoped HTTP contracts before wiring the analysis worker.
- Human validation: focused API suites green; hermetic pytest (~84%), ruff, mypy.

### 024 — Phase 11.8 hermetic analysis output routes (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial — analysis artefacts)
- Prompt intent: continue Phase 11 in the same PR; green the analysis/ranking reds.
- Suggestion: sync hermetic analyse on role create; routes for requirements,
  breakdown, gap-plan, interview-pack, bullets, cover-letter, export, ranking,
  compare using domain generation + scoring rubric.
- Outcome: accepted for hermetic API contracts; SQL persistence still deferred.
- Reason: artefact routes need a finished analysis; sync hermetic path keeps tests
  deterministic without a worker.
- Human validation: `pytest tests/api/test_role_analysis_routes.py
  tests/api/test_role_routes.py -q --no-cov` green (7 tests); ruff clean on changed
  files.

### 025 — Phase 11.8 hermetic role lifecycle and draft list (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial — lifecycle / drafts)
- Prompt intent: continue Phase 11 in the same PR.
- Suggestion: delete, reanalyse, cover-letter list, bullets/cover-letter export,
  analysis_incomplete coverage on the in-memory store.
- Outcome: accepted; SQL persistence still deferred.
- Reason: finish hermetic wire contracts before swapping stores for PostgreSQL.
- Human validation: lifecycle red→green; `pytest tests/api/ -q --no-cov` → 51
  passed; ruff and mypy clean on changed modules.

### 026 — Phase 11.8 SqlCvStore (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial — SQL CV persistence)
- Prompt intent: continue Phase 11; first SQL slice for API stores.
- Suggestion: SqlCvStore implementing CvStore over SqlUnitOfWork; integration tests
  for port + HTTP CV/span routes with injected store.
- Outcome: accepted; create_app still defaults to InMemoryCvStore for hermetic
  API tests.
- Reason: production CV data must hit PostgreSQL without breaking offline contract
  tests; injection keeps both paths.
- Human validation: integration SqlCvStore + CV HTTP SQL tests green; hermetic
  `tests/api/` green; ruff/mypy clean.

### 027 — Phase 11.8 SqlRoleStore (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial — SQL role/analysis persistence)
- Prompt intent: continue Phase 11 SQL slice after SqlCvStore.
- Suggestion: SqlRoleStore create/list/get/require_analysis publishing hermetic
  analysis; roles.company migration; create_app(role_store=…) injection.
- Outcome: accepted; delete/reanalyse/durable drafts deferred.
- Reason: prove role analysis rows round-trip through PostgreSQL before widening
  the store surface.
- Human validation: SqlRoleStore integration (2) green; related analysis/draft
  integration green; hermetic `tests/api/` green; ruff/mypy clean.

### 028 — Phase 11.8 SqlRoleStore delete and reanalyse (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial — SQL role lifecycle)
- Prompt intent: continue Phase 11 with TDD.
- Suggestion: RoleRepository.delete + bump_analysis_version; SqlRoleStore
  delete/reanalyse; version-scoped list_mappings; HTTP integration coverage.
- Outcome: accepted; durable drafts and production SQL default still deferred.
- Reason: finish role lifecycle persistence before draft durability.
- Human validation: 4 SqlRoleStore integration tests green; hermetic API and
  analysis persistence green; ruff/mypy clean.

### 029 — Phase 11.8 durable drafts on SqlRoleStore (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial — durable generated drafts)
- Prompt intent: continue Phase 11 with TDD.
- Suggestion: persist cover-letter/bullets through DraftRepository; prove survival
  across a fresh SqlRoleStore; reconstruct wires in analysis routes.
- Outcome: accepted; production SQL create_app default still deferred.
- Reason: generated artefacts must outlive the process like CV/roles.
- Human validation: durable-draft integration green; full SqlRoleStore + draft
  persistence suites green; hermetic API green; mypy/ruff clean.

### 030 — Phase 11.8 production SQL app wiring (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (complete — production entrypoint)
- Prompt intent: continue Phase 11; wire SQL as the uvicorn/Docker default.
- Suggestion: `build_sql_stores` + `create_production_app`; keep `create_app()`
  hermetic for API tests; unit-test module `app` store types.
- Outcome: accepted; 11.8 checked off in PLAN.md.
- Reason: AGENTS forbids process-memory as a production persistence path;
  Docker/Make run `career_assistant.main:app`.
- Rejected alternatives: changing `create_app()` default to SQL (would force
  every hermetic API test onto Postgres).
- Human validation: production wiring unit tests green; API suite green;
  `make lint` green.

### 031 — Phase 11.9 SSE answer stream (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.9
- Prompt intent: continue Phase 11 after production SQL wiring.
- Suggestion: API test for documented SSE sequence; `format_ask_sse` +
  `POST /api/messages` over AskService.stream; InMemoryConversationStore.
- Outcome: accepted; JSON Accept / GET / DELETE left for 11.13.
- Reason: Phase 9 already owns stream/non-stream parity in the use case; 11.9 is
  the HTTP transport framing only.
- Human validation: message SSE API test green; full API suite green; `make lint`
  green.

### 032 — Phase 11.10 answer and draft provenance (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.10
- Prompt intent: continue Phase 11 after SSE stream.
- Suggestion: API regression for provider/model/leftMachine on SSE meta, JSON
  ChatMessage, and draft/interview-pack provenance; extend AskEvent + SSE framing;
  add JSON Accept path sharing AskService.ask.
- Outcome: accepted; api-contract meta event updated with leftMachine.
- Reason: AGENTS requires every answer/artefact to record provider, model tag and
  egress; drafts already had DraftProvenanceWire.
- Human validation: provenance API tests green; API + ask use-case suites green;
  `make lint` green.

### 033 — Phase 11.11 OpenAPI and TypeScript type parity (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.11
- Prompt intent: continue Phase 11 after provenance.
- Suggestion: contract test mapping shared TS interfaces to OpenAPI components;
  require Evidence.spanId on both sides; update fixtures/client for the new fields.
- Outcome: accepted; PLAN 12.5 note adjusted so spanId is not re-added later.
- Reason: citations cannot open stored spans without spanId; contract file is the
  authority when halves disagree.
- Human validation: contract tests green; frontend typecheck/lint green; make lint
  green.

### 034 — Phase 11.12–11.13 supporting docs and message history (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.12, 11.13 (Phase 11 exit)
- Prompt intent: complete Phase 11 with TDD.
- Suggestion: supporting cover-letter CRUD + safe download; GET/DELETE messages;
  SSE replay messageId; error-table intake/provider coverage tests.
- Outcome: accepted; Phase 11 checked complete in PLAN.md.
- Reason: closes the remaining API contract surface before frontend integration.
- Rejected alternatives: SQL supporting/ask stores in this slice (hermetic first,
  matching prior Phase 11 pattern).
- Human validation: supporting + message history API tests green; full API suite
  green; make lint green.

### 048 — Phase 13.2 Gaps panel (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 13.2
- Prompt intent: continue Phase 13 after role tabs.
- Suggestion: GapsPanel presentational list from GET /gap-plan; Draft a bullet
  control when canDraftBullet; adjacent evidence opens shared EvidencePanel.
- Outcome: accepted.
- Reason: gap plan is deterministic server-side; UI only presents ordered items.
- Rejected alternatives: inventing gap order in the client (API already sorts by
  scoreDelta).
- Human validation: GapsPanel tests 2 green; full frontend vitest; tsc/lint.

### 047 — Phase 13.1 role detail tabs (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 13.1
- Prompt intent: continue Phase 13 after SQL supporting store.
- Suggestion: Fit/Gaps/Prepare/Letter tabs with `?tab=` deep-link search param;
  Gaps/Prepare/Letter placeholders until later slices.
- Outcome: accepted.
- Reason: matches features.md navigation; Fit keeps existing breakdown + table.
- Rejected alternatives: path segments per tab (search param is enough and keeps
  one route file).
- Human validation: RoleDetailTabs tests 3 green; full frontend vitest; tsc/lint.

### 046 — Phase 13 carry-forward: SQL supporting cover letters (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: Phase 12 exit-gate carry-forward into Phase 13
- Prompt intent: continue next phases after cover letters were not durable.
- Suggestion: SqlSupportingDocumentStore + wire into create_production_app /
  build_sql_stores.
- Outcome: accepted.
- Reason: Phase 12 exit gate already deferred SQL supporting store to Phase 13;
  uploads were process-memory only.
- Rejected alternatives: leaving cover letters in-memory until 13.5 Letter UI.
- Human validation: production wiring unit test; integration SQL store test;
  supporting API tests; ruff/mypy clean on touched modules.

### 045 — Phase 12 exit gate + Ask incomplete-analysis 409 (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: Phase 12 exit gate (plus defect found during it)
- Prompt intent: continue TDD with regular commits through Phase 12.
- Suggestion: run host API + Start proxy against sample fixtures; exercise UI;
  map Ask `RoleOperationRejected` to AppError 409.
- Outcome: accepted.
- Reason: exit gate requires a real backend path; 500 on incomplete analysis was
  a visible failure path bug.
- Rejected alternatives: declaring the gate met from unit tests alone; leaving
  Ask incomplete analysis as internal_error.
- Human validation: proxy walkthrough + browser role detail; SSE pytest green;
  frontend vitest 76 previously green for 12.12.

### 044 — Phase 12.12 wired screen component states (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.12
- Prompt intent: continue TDD with regular commits through Phase 12.
- Suggestion: prop-driven Vitest coverage for every wired presentational screen
  state (loading/empty/error/ready and analysis-status variants).
- Outcome: accepted.
- Reason: PLAN 12.12 requires component tests driven by props before the exit gate.
- Rejected alternatives: only container integration tests (would couple UI copy to
  network timing).
- Human validation: focused component tests green; full frontend vitest 76;
  typecheck/lint green.

### 043 — Phase 12.11 API error code → actionable UI (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.11
- Prompt intent: continue TDD with regular commits.
- Suggestion: describeApiError catalogue from api-contract; wire containers to use it.
- Outcome: accepted.
- Reason: unknown codes must fail visibly; known codes need a next step.
- Rejected alternatives: switching on message text.
- Human validation: errors tests green; full vitest 60; typecheck/lint.

### 042 — Phase 12.10 provider settings wiring (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.10
- Prompt intent: continue TDD with regular commits.
- Suggestion: re-index warning dialog; keep hosted confirm; show unavailableReason;
  setProviderChoice acknowledgedEgress + optional reindex response.
- Outcome: accepted.
- Reason: matches api-contract egress ack and index-change invalidation warning.
- Rejected alternatives: silent index changes without user confirmation.
- Human validation: ProviderSettings tests green; full vitest 56; typecheck/lint.

### 041 — Phase 12.9 Ask SSE wiring (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.9
- Prompt intent: continue TDD and commit regularly after 12.8.
- Suggestion: postMessageStream + ChatContainer real SSE; delete history; retry
  with stable clientRequestId; provider stamp includes leftMachine.
- Outcome: accepted.
- Reason: replaces fake token interval with the documented stream transport.
- Rejected alternatives: EventSource (POST body required).
- Human validation: stream tests green; full vitest 53; typecheck/lint green.

### 040 — Phase 12.8 role detail span resolution (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.8
- Prompt intent: continue Phase 12 after job polling.
- Suggestion: getSpan client; EvidencePanel loading/error resolve states;
  RoleDetailContainer fetches span when panel opens.
- Outcome: accepted.
- Reason: api-contract requires unresolved citations to fail visibly.
- Rejected alternatives: rendering inline requirement.evidence without a span GET.
- Human validation: spans + EvidencePanel tests green; full vitest 49; typecheck/lint.

### 039 — Phase 12.7 analysis job polling (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.7
- Prompt intent: continue Phase 12 after workspace wiring.
- Suggestion: getJob/reanalyseRole; RolesPanel Analysing/Failed/Retry; react-query
  refetchInterval on roles and jobs.
- Outcome: accepted.
- Reason: matches api-contract polling model without inventing a job list endpoint.
- Rejected alternatives: polling only the roles list (loses failure reason from job).
- Human validation: jobs + RolesPanel tests green; full frontend vitest 45;
  typecheck/lint green.

### 038 — Phase 12.6 workspace upload wiring (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.6
- Prompt intent: continue Phase 12 in TDD after additive types.
- Suggestion: multipart `uploadCv`/`uploadCoverLetter`; backend multipart routes;
  confirmations; cover-letter “not score evidence” card; ApiError messages in UI.
- Outcome: accepted; added `python-multipart` dependency.
- Reason: api-contract already required multipart; paste-only could not admit PDF/DOCX.
- Rejected alternatives: reading PDF client-side into paste JSON; deferring multipart
  to a later phase.
- Human validation: upload + component tests green; CV/supporting API tests green;
  frontend typecheck/lint green; locks regenerated.

### 037 — Phase 12.5 additive frontend types (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.5
- Prompt intent: continue Phase 12 in TDD style after 12.3–12.4.
- Suggestion: additive types from api-contract; Role.status/updatedAt; extend
  OpenAPI↔TS contract suite.
- Outcome: accepted.
- Reason: screens for gaps/prepare/letter need typed contracts before wiring.
- Rejected alternatives: optional Role.status (API always returns it; required
  keeps the list UI honest for 12.7 polling).
- Human validation: additive + client tests green; full frontend vitest 33 green;
  OpenAPI contract pytest green; typecheck/lint green.

### 036 — Phase 12.3–12.4 real HTTP client and fixture move (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.3, 12.4
- Prompt intent: continue Phase 12 in TDD style.
- Suggestion: zod schemas + `request()`/`ApiError` client; move fixtures to
  `__fixtures__/`; ban fixture imports from components.
- Outcome: accepted.
- Reason: screens already call `@/api/client`; swapping the implementation keeps
  signatures and removes mock data from the production path.
- Rejected alternatives: keeping fixtures co-located with `client.ts`; CORS
  browser client (proxy already proven).
- Human validation: client tests 6 green; fixtures + eslint-guard tests green;
  typecheck and lint green.

### 035 — Phase 12.1–12.2 API proxy spike and catch-all (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.1, 12.2
- Prompt intent: continue to Phase 12; spike SSE/upload through Start, then proxy.
- Suggestion: `proxyToUpstream` with Node http spike tests; `src/routes/api.$.ts`
  catch-all; record pass on ADR 006 / PLAN.
- Outcome: accepted; spike passed — no CORS fallback.
- Reason: ADR 006 risk was buffering in the Node proxy; proofs close that risk
  before the real client depends on it.
- Human validation: api-proxy tests (6) green; full frontend vitest (12) green;
  typecheck/lint green.
