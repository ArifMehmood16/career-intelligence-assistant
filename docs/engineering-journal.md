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

## Phase 10 — Grounded generation (complete, including 10.9)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/integration/test_draft_persistence.py -m integration -q --no-cov`
  - `make db-migrate` (revision `71f0c6b9147f`)
  - `pytest -m integration -q --no-cov`, `pytest -q`, `ruff`, `mypy`
- Observed result:
  - Drafts persist body, citations, provider/model, `left_machine`, groundedness,
    template-fallback flag and regeneration count.
  - Regeneration allocates immutable `version` per `(role, kind)`; FAIL groundedness
    rejected at save.
- Decisions made: SQL draft repo omitted from hermetic coverage (integration-proven);
  HTTP draft routes remain Phase 11.
- Problems hit: none material.
- Carried forward: Phase 11 API contracts.

## Phase 10 — Grounded generation (10.1–10.8)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_groundedness.py -q --no-cov`
  - `pytest tests/unit/test_gap_plan.py -q --no-cov`
  - `pytest tests/unit/test_generation_pipeline.py -q --no-cov`
  - `pytest tests/unit/test_interview_export.py -q --no-cov`
  - `pytest -q`, `ruff`, `mypy`
- Observed result:
  - Adversarial groundedness fixtures fail closed; case variants pass.
  - Gap plan ordered by scoreDelta; evidence_it vs learn_it/accept_it.
  - Pipeline: validate → one regenerate → template fallback with counters.
  - Hermetic bullets; cover letter refuses below two met must-haves.
  - Interview pack sections from mapping; markdown export byte-stable.
- Decisions made: 10.9 PostgreSQL artefact versions deferred to a follow-up slice.
- Problems hit: none material.
- Carried forward: 10.9 persistence; Phase 11 API routes.

## Phase 9 — Question answering (complete)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_ask_use_case.py -q --no-cov`
  - `pytest tests/integration/test_ask_persistence.py -m integration -q --no-cov`
  - `pytest -m integration -q --no-cov`, `pytest -q`, `ruff`, `mypy`
- Observed result:
  - `AskService.ask` / `.stream` share one produce path; tokens never persisted mid-stream.
  - Question committed before answer; `clientRequestId` returns existing pair.
  - SQL `get_by_client_request_id`, `list_history`, citation list, hard delete.
- Decisions made: HTTP `/api/messages` remains Phase 11; behaviour proven at use-case
  + repository layers.
- Problems hit: same-timestamp history order — tests use ordered UUIDs; schema-
  qualified raw SQL in hard-delete assertions.
- Carried forward: Phase 10 grounded generation; wire AskService in Phase 11.

## Phase 9 — Question answering (domain slice)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_intent_router.py -q --no-cov`
  - `pytest tests/unit/test_structured_ask.py -q --no-cov`
  - `pytest tests/unit/test_open_question_prompt.py -q --no-cov`
  - `pytest -q`, `ruff`, `mypy`
- Observed result:
  - Deterministic `route_intent` for gaps/fit/compare/evidence/interview/open.
  - `answer_structured` builds answers from mappings only; bad citations →
    insufficient.
  - Open-question span selection respects cover-letter ask + role JD isolation;
    prompts delimit untrusted text and enforce budgets.
- Decisions made:
  - TDD red commits before each green slice; Phase 9 exit gate still needs
    streaming + persistence (9.7–9.9).
- Problems hit and how they were resolved: mypy loop-variable shadowing in compare.
- Carried forward: 9.7–9.9 application/API persistence and streaming.

## Phase 8 — Analysis jobs

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_analysis_job_domain.py -q --no-cov` (red then green)
  - `pytest tests/unit/test_analysis_pipeline.py -q --no-cov` (red then green)
  - `pytest tests/integration/test_analysis_persistence.py -m integration -q --no-cov`
  - `pytest -m integration -q --no-cov`, `pytest -q`, `ruff`, `mypy`
- Observed result:
  - Domain job lifecycle with stages, safe errors, stale-running recovery.
  - `AnalysisService` enqueues immediately, bounds concurrency, publishes only on
    success, discards on failure; CV-replace reanalysis covered in unit + SQL.
  - Migration `34b3a0846d82` adds role `status` and full job columns; SQL repos
    publish requirements/claims/mappings/score + terminal job atomically.
- Decisions made:
  - Red tests committed before each green implementation (team TDD).
  - SQL analysis repos omitted from hermetic coverage; proven by integration.
- Problems hit and how they were resolved:
  - Duplicate test module basename (`test_analysis_jobs.py`); renamed unit vs
    integration modules.
- Carried forward: Phase 9 question answering; HTTP role/job routes in Phase 11.

## Phase 7 — Mapping and scoring

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_mapping_scoring.py -q --no-cov`
  - `pytest -q`, `ruff check`, `ruff format`, `mypy`
- Observed result:
  - Domain `map_requirement` / `map_requirements` → `met` / `partial` / `missing`
    with reason codes and justifying span/claim ids; no I/O.
  - Optional similarity scores may surface candidates; high similarity alone never
    forces `met`.
  - `score_fit` reads `config/scoring_rubric.toml` via `load_scoring_rubric`;
    components and bands are deterministic; counterfactual delta is pure.
  - Fixture JD + CV (rules extractors) produce a stable score with no model call.
- Decisions made:
  - Mapping and scoring stay pure in `domain/`; rubric loading is application-layer
    configuration, not domain env access.
- Problems hit and how they were resolved:
  - Ruff E501 on long policy lines; reformatted with wrapped conditions / key helper.
- Carried forward: Phase 8 analysis jobs.

## Phase 6 — Evidence extraction

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_claim_extraction.py -q --no-cov`
  - `pytest -q`, `ruff check`, `mypy`
- Observed result:
  - Domain `Claim` plus pure `derive_recency_signal` / `derive_duration_signal`.
  - Rules extractor reads EXPERIENCE bullets with role date ranges; undated stays
    undated; dated-experience Spark claims are not recent.
  - Span validation drops bad refs; cover letters rejected; model path keeps only
    span-backed texts.
- Decisions made:
  - Recency uses injectable `as_of` for deterministic tests (default `date.today()`).
- Problems hit and how they were resolved: none material.
- Carried forward: Phase 7 mapping and scoring.

## Phase 5 — Requirement extraction

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_requirement_extraction.py -q --no-cov`
  - `pytest -q`, `ruff check`, `mypy`
- Observed result:
  - Domain `Requirement` with competency, seniority, must-have, confidence, vagueness.
  - `RulesRequirementExtractor` parses must/desirable bullet sections with exact spans.
  - Span validation drops non-resolving refs; injection fixture adds no override reqs.
  - Vague seniority fixture marks unquantified signals; cover letters are rejected.
  - Model-backed path uses CompletionPort JSON schema and keeps only span-backed texts.
- Decisions made:
  - Rules adapter remains the default; model path intersects model texts with rule
    spans so invented requirements cannot pass without a stored substring.
- Problems hit and how they were resolved: none material.
- Carried forward: Phase 6 evidence / claims extraction.

## Phase 4 — Persistence

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_database_settings.py … --no-cov` — red on missing
    `DatabaseSettings`, then green.
  - `pytest -m integration -q --no-cov` against local `career_assistant_test`
  - `pytest -q`, `ruff check`, `mypy`
  - `make db-check`, `make db-migrate`
- Observed result:
  - `DatabaseSettings` enforces `postgresql+psycopg://`, separate test URL, bounded
    pool/timeouts, and `hide_parameters` on the engine.
  - Alembic baseline creates `vector` plus the Phase 4 table set; upgrade/downgrade
    round-trips on an empty database.
  - Repository ports + `SqlUnitOfWork` store CV/cover-letter bytes with spans,
    workspace-scope reads, hard delete, CV replacement invalidation, and conversation
    uniqueness constraints.
  - `make db-check` / `make db-migrate` / `make run` use local `DATABASE_URL`.
- Decisions made:
  - Embedding column is `vector(64)` matching the hermetic default; dimensions are
    also stored per row. Hosted dims with a different size need a later migration.
  - SQLAlchemy stays under `adapters/persistence/` with a dedicated boundary guard.
- Problems hit and how they were resolved:
  - Answer citations flushed before the parent answer; fixed by flushing the answer
    first.
  - Local role `career` and databases created for integration runs; Docker was not
    required.
- Carried forward:
  - Phase 5 requirement extraction; HTTP upload routes still Phase 11.

## Phase 3 — Document intake and spans

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_document_intake.py -q --no-cov` — observed red on missing
    `parsing.pipeline` and a ligature fixture typo; then green after implementation.
  - `pytest -q`, `ruff check`, `mypy`
- Observed result:
  - Domain `Document` / `Page` / `Span` with offset-backed citation units.
  - Admission sniffs PDF/DOCX/plain text; maps oversized and unsupported inputs to
    api-contract codes.
  - Normalisation expands ligatures/bullets and joins hyphenated line breaks; paragraph
    offsets round-trip.
  - Pipeline parses plain text fixtures plus synthetic PDF/DOCX bytes; encrypted and
    empty PDFs raise `document_unreadable`.
  - Span resolution guarantees `highlight ⊆ paragraph`.
- Decisions made:
  - Add `pypdf`, `python-docx`, and `cryptography` (AES encrypt fixtures / PDF crypto).
  - Generate PDF/DOCX test bytes in `tests/support` rather than committing binaries.
- Problems hit and how they were resolved:
  - Ligature test used `e`+`ﬁ`+`cient` (eficient); corrected to `ef`+`ﬁ`+`cient`.
  - TDD: failing tests committed first, then the pipeline implementation.
- Carried forward:
  - Phase 4 persistence; HTTP upload routes still later (Phase 11).

## Phase 2 — Model providers

- Date: 2026-09-18
- Commands run:
  - `backend/.venv/bin/pytest tests/contract tests/unit/test_providers.py -q --no-cov`
  - `backend/.venv/bin/pytest -q` (full hermetic suite)
  - `backend/.venv/bin/ruff check src tests`, `mypy`
- Observed result:
  - Completion and embedding ports live under `application/ports/` with no vendor
    shapes; capability descriptors drive behaviour.
  - Hermetic adapters are the default; Ollama/OpenAI/Anthropic use injectable HTTP
    transports and recorded fixtures in the shared contract suite (no live calls).
  - Hosted adapters raise `EgressNotPermittedError` when the gate is closed or the
    key is missing; scripted transport records zero calls in that case.
  - Resilience (retry 429/5xx, breaker), explicit fallback flag, call accounting, and
    `ProviderSettings.public_snapshot()` key redaction are covered by unit tests.
  - Coverage 86% on the package; architecture guard still forbids SDKs in
    domain/application.
- Decisions made:
  - Use `httpx` as the only runtime HTTP client for provider adapters (no vendor
    SDKs in the lock yet).
  - Anthropic embedding requests fail closed at the factory — ports stay independent.
- Problems hit and how they were resolved:
  - Needed `pythonpath = ["src", "."]` so contract tests can import `tests.support`.
- Carried forward:
  - Phase 3 document intake and spans.
  - Provider HTTP routes and workspace selection land in Phase 11 / 4.

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
