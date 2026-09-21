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

## Phase 13A.5 — Database-backed retrieval and span resolution

- Date: 2026-09-21
- Commands run:
  - `pytest tests/api/test_span_routes.py::test_get_span_returns_evidence_for_uploaded_cover_letter -q --no-cov` — red first (404); then green after workspace span lookup
  - `pytest tests/api/test_span_routes.py::test_get_span_returns_evidence_for_role_job_description -q --no-cov` — red first (404); then green after role-store `get_span`
  - `pytest tests/api/test_retrieval_http.py -q --no-cov` — red first (cover-letter and same-role JD ids absent from Ask citations); then green after retrieval pool
  - `pytest -m integration tests/integration/test_retrieval_http_sql.py -q --no-cov` — 4 passed against PostgreSQL
  - `make test` — 242 passed, 3 skipped, 46 deselected; coverage 80.12%; frontend Vitest 100 passed / 32 files
  - `make test-integration` — 46 passed
  - `make lint` — ruff, mypy 119 files, frontend tsc and eslint green
- Observed result: `GET /api/spans/{id}` and generated-artefact evidence share one workspace-scoped resolver over the active CV, uploaded cover letters and role JD spans. Open questions retrieve those same kinds; a role-scoped question cannot cite another role's JD. Cover-letter text that would meet a requirement if it were a CV does not change mappings or scores. Cross-workspace span GET returns `span_not_found`. The same behaviours hold on SQL stores.
- Decisions made: lookup lives in application code (`lookup_workspace_span` / `retrieval_pool`); HTTP routes only translate. SQL finds any stored span row by workspace id, then filters by document kind at the supporting/role adapters.
- Problems hit: first JD GET fixture had no bullets so rules extraction produced no spans; switched to a Requirements list. Cover-letter Ask first asserted `spans[0]`, which was the greeting paragraph; the test now selects the Kubernetes span.
- Carried forward: 13A.6 route generated prose through the grounded-generation use case.

## Phase 13A.4 — Provider selection drives extraction, Ask and phrasing

- Date: 2026-09-21
- Commands run:
  - `pytest tests/api/test_provider_runtime_selection.py::test_open_question_calls_the_selected_scripted_provider -q --no-cov` — red first (`provider` was `hermetic`); then green after Ask used the workspace choice
  - `pytest tests/unit/test_providers.py::test_complete_rechecks_egress_and_makes_no_network_call -q --no-cov` — red first (DID NOT RAISE); then green after call-time egress wrap
  - `pytest tests/api/test_provider_runtime_selection.py::test_requirement_extraction_calls_the_selected_scripted_provider -q --no-cov` — red first (`transport.calls` empty); then green
  - `pytest tests/api/test_provider_runtime_selection.py::test_bullet_phrasing_calls_the_selected_scripted_provider -q --no-cov` — red first (`provider` was `hermetic`); then green
  - `pytest tests/api/test_provider_runtime_selection.py::test_open_question_records_accounting_without_document_text -q --no-cov` — red first (no `call_accountant`); then green
  - `make test` — 236 passed, 3 skipped, 42 deselected; coverage 80.61%; frontend Vitest 100 passed / 32 files
  - `make test-integration` — 42 passed
  - `make lint` — ruff, mypy 118 files, frontend tsc and eslint green
- Observed result: persisted answer provider is used for open questions, requirement/claim extraction (non-hermetic) and bullet phrasing. Completion and embedding choices stay independent. Hosted egress is checked at construction and again on `complete()`. A rejected hosted choice returns 403 with no transport calls. Answers, bullets and interview/cover-letter provenance come from the selected completion port rather than a hard-coded hermetic tag. Call accounting stores provider/model/`left_machine` and token counts, never document text; SQL-backed apps write `provider_call_accounting` rows.
- Decisions made: hermetic `create_app()` still defaults completion/embedding to hermetic so env `COMPLETION_PROVIDER=openai` cannot leak into API tests. Hermetic analysis stays on rules extractors; model-backed extractors wrap the Phase 2 factory only when the workspace answer choice is not hermetic. Local fallback never swallows `EgressNotPermittedError`.
- Problems hit: wrapping analysis in `Model*Extractor` for the hermetic default dropped SQL fit scores to 0 because hermetic structured output did not map cleanly; restored rules for hermetic choice. Env-hosted `ProviderSettings()` on the SQL worker similarly tried a real OpenAI call in integration tests; worker defaults without injected settings stay hermetic.
- Carried forward: 13A.5 database-backed retrieval and span resolution.

## Phase 13A.3 — PostgreSQL-backed analysis worker

- Date: 2026-09-21
- Commands run:
  - `pytest tests/integration/test_analysis_worker_http_sql.py::test_post_role_returns_analysing_and_queued_before_worker_runs -m integration --no-cov` — red first (`ready` vs `analysing`); then green after enqueue-only `create_role`
  - focused worker / SQL role / chat / CV / wiring tests — green
  - `make test` — 230 passed, 3 skipped, 40 deselected; coverage 80.04%; frontend Vitest 100 passed / 32 files
  - `make test-integration` — 40 passed
  - `make lint` — ruff, mypy 115 files, frontend tsc and eslint green
- Observed result: production SQL `POST /roles` and reanalyse commit `analysing` plus a queued job and return 202 before extraction. The in-process worker publishes or fails transactionally. CV replace enqueues job ids in the same transaction and never leaves a role `ready` with a stale score. CV delete marks roles `failed`. Startup recovers queued jobs and fails stale-running ones. Hermetic `create_app()` stays in-memory and still returns `ready` immediately.
- Decisions made: hermetic API tests keep the synchronous in-memory store; only the SQL path is asynchronous. Worker extractors remain hermetic until 13A.4. No Celery.
- Problems hit: existing SQL role/chat tests assumed in-request `ready`/`succeeded` — they now drain the worker. `fail_job` deletes only the current analysis version so sibling-role claims are not wiped.
- Carried forward: 13A.4 provider selection must affect actual extraction and answers.

## Phase 13A.2 — SQL chat and provider settings

- Date: 2026-09-21
- Commands run:
  - `pytest tests/integration/test_chat_provider_http_sql.py::test_messages_survive_fresh_app_process -m integration` — red first on empty FIT citations and a doubled check-constraint name; then green
  - focused hermetic ask/message/provider/wiring tests — 19 passed
  - `make test` — 230 passed, 3 skipped, 33 deselected; coverage 80.28%; frontend Vitest 100 passed / 32 files
  - `make test-integration` — 33 passed
  - `make lint` — ruff, mypy 114 files, frontend tsc and eslint green
- Observed result: production `create_production_app` wires SQL conversation and provider-choice stores. Questions, answers, citations, idempotent retries, deletion and provider model tags survive a fresh app process and stay workspace-scoped. `create_app()` remains in-memory for hermetic API tests.
- Decisions made: UUID answer ids from `id_factory`; additive `answers.kind` and provider model-tag columns; one conversation per workspace; local personal-use security posture documented (no multi-user auth in this build).
- Problems hit: FIT answers have empty citations by design — survival test uses an evidence question. Alembic naming doubled `ck_answers_answer_kind`.
- Carried forward: 13A.3 PostgreSQL-backed analysis worker in production.

## Phase 13A.1 — Restore the complete quality baseline

- Date: 2026-09-18
- Commands run:
  - `backend/.venv/bin/ruff format --check backend/src backend/tests` — 168 files
    already formatted after collapsing `list_cover_letters` in
    `application/ports/persistence.py`
  - `make lint` — ruff check/format green; mypy "Success: no issues found in 111
    source files"; frontend `tsc --noEmit` and `eslint .` green
  - `make typecheck` — mypy 111 files; frontend `tsc --noEmit` green
  - `make test` — backend 230 passed, 3 skipped, 29 deselected, 2 warnings;
    coverage 80.58%; frontend Vitest 100 passed / 32 files
  - `make test-integration` — 29 passed against local PostgreSQL; same 2 warnings
- Observed result: exact Make quality targets are green without changing Ruff's
  `backend/src backend/tests` scope. Alembic versions remain in
  `backend/migrations/`, outside that target.
- Decisions made: carry the two TestClient deprecation warnings as a Phase 15
  maintenance risk rather than adding `httpx2`, widening FastAPI, or filtering
  warnings.
- Problems hit: `list_cover_letters` was the only unformatted signature.
- Carried forward: 13A.2 SQL-backed chat and provider settings.

## Phase 13 — Accessibility and escaped text (13.9–13.10) + exit gate

- Date: 2026-09-18
- Commands run:
  - `bun run test src/a11y/phase13-accessibility.test.tsx` — 3 passed
  - `bun run test src/a11y/phase13-escaped-text.test.tsx` — 2 passed
  - `bun run test` — 100 passed / 32 files
  - `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: live regions on parsing, analysing, streaming; XSS strings stay
  text; Phase 13 exit gate met for frontend quality checks.
- Decisions made: polite live regions only.
- Problems hit: duplicate Analysing status in table+cards layouts — tests use
  getAllByRole.
- Carried forward: Phase 14 Evaluation.

## Phase 13 — /dev/states gallery (13.8)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/routes/dev.states.test.tsx` — 1 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: gallery lists Phase 13 surfaces; smoke test asserts every
  DEV_STATE_SECTION_TITLES h2 is present.
- Decisions made: export DevStatesPage + title list for the smoke test.
- Problems hit: getByRole heading name matching was flaky vs nested content;
  smoke test uses h2 text selector.
- Carried forward: 13.9 Accessibility.

## Phase 13 — Compare (13.7)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/workspace/ComparePanel.test.tsx` — 2 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: workspace Compare picks two roles, shows shared/unique/
  differentiator, and links into Gaps.
- Decisions made: only ready roles appear in the selectors.
- Problems hit: none material.
- Carried forward: 13.8 `/dev/states`.

## Phase 13 — Ranking (13.6)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/workspace/RankingPanel.test.tsx` — 2 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: workspace shows ranked roles with because lines and Tied labels.
- Decisions made: RankingPanel sits below RolesPanel on `/`.
- Problems hit: none material.
- Carried forward: 13.7 Compare.

## Phase 13 — Letter tab (13.5)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/role/LetterPanel.test.tsx` — 3 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: Letter tab drafts via POST /cover-letter, lists versions,
  exports Markdown, refuses with Open Gaps, and lists workspace supporting uploads
  separately.
- Decisions made: citation chips use span ids resolved through EvidencePanel.
- Problems hit: none material.
- Carried forward: 13.6 Ranking.

## Phase 13 — Prepare / interview pack (13.4)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/role/PreparePanel.test.tsx` — 2 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: Prepare tab shows probes, lead-with, thin areas, ask-them;
  evidence is clickable; Export Markdown downloads the artefact.
- Decisions made: empty when all four sections are empty arrays.
- Problems hit: none material.
- Carried forward: 13.5 Letter tab.

## Phase 13 — Bullet drafts (13.3)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/role/BulletDraftPanel.test.tsx` — 2 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: Draft a bullet POSTs /bullets and shows text, citation chips,
  provenance, copy, and template-fallback status.
- Decisions made: draft panel sits under the Gaps list; dismiss resets the mutation.
- Problems hit: none material.
- Carried forward: 13.4 Prepare tab.

## Phase 13 — Gaps panel (13.2)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/role/GapsPanel.test.tsx` — 2 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: Gaps tab lists ordered gap items with reason, score delta,
  action, adjacent evidence, and Draft a bullet when canDraftBullet.
- Decisions made: draft click is wired as a no-op until 13.3; evidence reuses
  EvidencePanel via a synthetic Requirement selection.
- Problems hit: none material.
- Carried forward: 13.3 bullet draft surface.

## Phase 13 — Role detail tabs (13.1)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/role/RoleDetailTabs.test.tsx` — 3 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: role detail has Fit/Gaps/Prepare/Letter tabs; `?tab=gaps`
  deep-links; arrow keys move focus across the tablist.
- Decisions made: optional search param `tab` (default Fit); later panes are
  placeholders until 13.2–13.5.
- Problems hit: macOS case-insensitive clash between RoleDetailTabs.tsx and
  roleDetailTabs.ts — renamed constants module to role-detail-tabs.ts.
- Carried forward: 13.2 Gaps content.

## Phase 13 — SQL supporting cover letters (carry-forward)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_production_app_wiring.py tests/integration/test_sql_supporting_store.py tests/api/test_supporting_documents.py -q --no-cov`
  - ruff check + mypy on touched modules
- Observed result: production app wires SqlSupportingDocumentStore; cover letters
  persist in PostgreSQL documents (kind=cover_letter) with list/delete/download.
- Decisions made: close Phase 12 carry-forward before 13.1 UI tabs.
- Problems hit: none material.
- Carried forward: 13.1 role detail tabs; chunk/embedding index path; model-backed
  SqlRoleStore analysis.

## Phase 12 — Frontend integration (exit gate)

- Date: 2026-09-18
- Commands run:
  - Host API: `COMPLETION_PROVIDER=hermetic EMBEDDING_PROVIDER=hermetic
    EXTRACTION_STRATEGY=rules uvicorn … :8000` (overrides `config/app.env` ollama)
  - Frontend: `API_BASE_URL=http://127.0.0.1:8000 bun run dev -- --host 127.0.0.1`
  - Proxy walkthrough: POST `/api/cv` with `sample-data/fixtures/resumes/cv-strong-match.txt`,
    POST `/api/roles` with `jd-clean-match.txt`, poll job → succeeded, requirements/
    breakdown/SSE Ask tokens, pages `/` `/settings` `/ask` `/dev/states` → 200
  - Failure paths: empty file → `document_unreadable` 422; JPEG →
    `document_unsupported` 415; missing span → `span_not_found` 404; Ask with
    incomplete analysis → `analysis_incomplete` 409 (after fix)
  - Browser: workspace empty → upload CV → add role → score 73 / Partial match →
    role detail breakdown + requirements
  - `bun run test` — 76; Ask SSE pytest — 2 green after 409 mapping
- Observed result: Phase 12 exit gate criteria met for the wired screens; no mock
  data in `src/api/client.ts`.
- Decisions made: exit gate verified on hermetic providers, not the ollama values
  currently in `config/app.env`.
- Problems hit and how they were resolved:
  - Proxy mutations need `Origin` matching the app origin (csrf).
  - Dev server needs `API_BASE_URL` in the process environment.
  - Ask against incomplete analysis returned 500; mapped `RoleOperationRejected`
    to `AppError` (TDD).
- Carried forward:
  - Production supporting-document store still in-memory.
  - Playwright e2e (16.5); Docker image/stack (16.1).
  - Phase 13 new screens.

## Phase 12 — Frontend integration (12.12 wired screen states)

- Date: 2026-09-18
- Commands run:
  - `bun run test` (frontend) — 76 passed across 21 files
  - `bun run lint` — clean
  - `bunx tsc --noEmit` — clean
- Observed result:
  - Prop-driven state coverage for RolesPanel, CvCard, CoverLettersCard,
    FitBreakdown, RequirementTable, RoleHeader, ChatView, ProviderSettings
    (loading / empty / error / ready as applicable), plus prior EvidencePanel
    resolve states.
- Decisions made: none beyond the task.
- Problems hit and how they were resolved:
  - RequirementTable ready row text appears in table and card layouts; tests click
    `getAllByText(...)[0]`.
- Carried forward: Phase 12 exit gate against a running backend.

## Phase 12 — Frontend integration (12.11 error mapping)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/api/errors.test.ts` (red then green)
  - `bun run test` / `bun run typecheck` / `bun run lint`
- Observed result:
  - `describeApiError` covers every documented contract code; unknown codes surface
    with correlation id; wired into CV, roles, cover letters, chat, settings, and
    span resolve paths.
  - Frontend vitest 60 green.
- Decisions made: switch on code only; keep server `message` and append next-step copy.
- Problems hit: none after prettier.
- Carried forward: 12.12 component tests for wired screens.

## Phase 12 — Frontend integration (12.10 settings)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/settings/ProviderSettings.test.tsx` (red then green)
  - `bun run test` / `bun run typecheck` / `bun run lint`
- Observed result:
  - Unavailable reasons rendered from the API; hosted egress dialog retained;
    re-index confirmation when index provider/model changes; save errors surfaced
    from ApiError; setProviderChoice returns optional reindex job id.
  - Frontend vitest 56 green.
- Decisions made: warn before PUT on index changes (UI gate); hosted still requires
  acknowledgement; acknowledgedEgress only when a hosted provider is in the choice.
- Problems hit: duplicate reason text across answer/index selectors in tests.
- Carried forward: 12.11 error-code mapping across the app.

## Phase 12 — Frontend integration (12.9 Ask SSE)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/api/stream.test.ts` (red then green)
  - `bun run test` / `bun run typecheck` / `bun run lint`
- Observed result:
  - `postMessageStream` parses documented SSE events; ChatContainer streams tokens,
    stops via AbortController, deletes history, retries with the same
    `clientRequestId`, and resolves citation spans.
  - Frontend vitest 53 green.
- Decisions made: keep JSON `sendMessage` helper; Ask path uses SSE only.
- Problems hit: none after prettier/index-signature fixes.
- Carried forward: 12.10 settings wiring.

## Phase 12 — Frontend integration (12.8 role detail + span resolve)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/api/spans.test.ts src/components/EvidencePanel.test.tsx`
    (red then green)
  - `bun run test` / `bun run typecheck` / `bun run lint`
- Observed result:
  - `getSpan` client helper; role detail resolves selected evidence via
    `GET /api/spans/{id}`; unresolvable spans show a visible error (not the empty
    “no supporting text” copy).
  - Frontend vitest 49 green.
- Decisions made: always re-fetch by `spanId` when present rather than trusting
  inline requirement evidence alone.
- Problems hit: none after prettier fix.
- Carried forward: 12.9 Ask SSE wiring.

## Phase 12 — Frontend integration (12.7 analysis job polling)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/api/jobs.test.ts src/components/workspace/RolesPanel.test.tsx`
    (red then green)
  - `bun run test` / `bun run typecheck` / `bun run lint`
- Observed result:
  - `getJob` / `reanalyseRole` client helpers; roles query refetches while any role
    is `analysing`; job query polls while `queued`/`running`.
  - Roles list shows Analysing / Failed (+ reason + Retry analysis).
  - Frontend vitest 45 green.
- Decisions made: map OpenAPI string `AnalysisJob.error` to
  `{ code: "analysis_failed", message }` on the client; track role→jobId in
  container state from create/reanalyse responses.
- Problems hit: none material after exactOptionalPropertyTypes FitCell fix.
- Carried forward: 12.8 wire role detail.

## Phase 12 — Frontend integration (12.3–12.6 client, types, workspace)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/api/client.test.ts` / `src/api/upload.test.ts` /
    `src/types/additive.test.ts` (red then green)
  - `bun run test` / `bun run typecheck` / `bun run lint`
  - `backend/.venv/bin/pytest tests/contract/test_openapi_frontend_types.py -q --no-cov`
  - `backend/.venv/bin/pytest tests/api/test_cv_routes.py tests/api/test_supporting_documents.py -q --no-cov`
  - `make lock` (python-multipart)
- Observed result:
  - Real HTTP client with zod; fixtures under `__fixtures__/`; additive types;
    multipart CV/cover-letter upload on API + frontend; workspace shows ApiError
    rejection messages, replace/delete confirmations, supporting cover letters with
    “not score evidence” notice.
  - Frontend vitest 39 green; CV/supporting API tests green.
- Decisions made: add `python-multipart` for Starlette form parsing; keep paste
  JSON path alongside multipart; upload progress UI uses parsing busy state (byte
  progress deferred until XHR helper if needed).
- Problems hit: nested-brace TS parser for Role; exactOptionalPropertyTypes on
  fetch init / ChatMessage mapping.
- Carried forward: 12.7 analysis job polling.

## Phase 12 — Frontend integration (12.1–12.2 proxy spike and catch-all)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/server/api-proxy.test.ts`
  - `bun run test` / `bun run typecheck` / `bun run lint`
  - `@tanstack/router-cli generate` (route tree includes `/api/$`)
- Observed result:
  - Spike **pass**: first SSE event arrives before upstream finishes; streaming
    upload body is forwarded without `arrayBuffer`/`text`/`json`; upstream reads
    the first byte before the client stream closes.
  - `src/routes/api.$.ts` proxies `/api/**` to `API_BASE_URL` with same-origin
    checks on non-GET.
- Decisions made: keep Start proxy path (no ADR CORS fallback); `API_BASE_URL`
  remains server-only.
- Problems hit: none after prettier fix.
- Carried forward: 12.3 real HTTP client replacing fixture `client.ts`.

## Phase 11 — API contracts (complete)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_supporting_documents.py` (red→green)
  - `pytest tests/api/test_message_history.py` (red→green)
  - `pytest tests/api -q --no-cov`
  - `pytest tests/api/test_error_table_coverage.py`
  - `make lint`
- Observed result:
  - Supporting cover letters: list/upload/delete + safe document download.
  - Messages: GET history, DELETE hard-delete, JSON/SSE share answer id on retry.
  - Full API suite green; lint/mypy/frontend typecheck green.
- Decisions made: hermetic InMemorySupportingDocumentStore (CV download bridge);
  conversation store remains process-local for API tests (SQL ask store deferred).
- Problems hit: download route needed response_class for the response_model gate;
  SSE replay omitted messageId until fixed.
- Carried forward: Phase 12; SQL supporting/ask stores; rate_limited/provider_failed
  HTTP surfaces when those controls exist.

## Phase 11 — API contracts (11.11 OpenAPI↔TS types)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/contract/test_openapi_frontend_types.py -q --no-cov` (red then green)
  - `make lint` / frontend `tsc` / `eslint`
- Observed result:
  - Shared models assert required camelCase fields on both OpenAPI and
    `frontend/src/types/index.ts`.
  - `Evidence.spanId` added to TS; fixtures and mock client updated.
  - `ChatMessage.leftMachine` (+ question kind) aligned with the wire contract.
- Decisions made: required-field intersection test (API may add fields); bring
  spanId forward from the Phase 12.5 note into 11.11 as PLAN requires.
- Problems hit: none after fixture/client updates.
- Carried forward: 11.12 supporting documents; 11.13 GET/DELETE messages + SQL.

## Phase 11 — API contracts (11.10 answer/draft provenance)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_provenance_responses.py -q --no-cov` (red then green)
  - `pytest tests/api tests/unit/test_ask_use_case.py -q --no-cov`
  - `make lint`
- Observed result:
  - SSE meta carries provider, model, leftMachine.
  - JSON Accept on POST /messages returns ChatMessageWire with the same fields.
  - Interview pack, bullets, cover-letter provenance already present — locked by
    regression.
- Decisions made: extend AskEvent/SSE meta with leftMachine; document it in
  api-contract.md; JSON ask path added early for provenance (GET/DELETE still 11.13).
- Problems hit: none after green.
- Carried forward: 11.11 OpenAPI↔TS; 11.12 supporting docs; 11.13 history/delete.

## Phase 11 — API contracts (11.9 SSE ask stream)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_message_sse.py -q --no-cov` (red then green)
  - `pytest tests/api -q --no-cov`
  - `make lint`
- Observed result:
  - `POST /api/messages` with `Accept: text/event-stream` returns
    meta → token(s) → citations → done over hermetic AskService.
  - Response-model gate allows StreamingResponse alongside PlainTextResponse.
- Decisions made: SSE framing in `api/sse.py`; in-memory conversation store for
  hermetic API; JSON Accept deferred to 11.13 with GET/DELETE.
- Problems hit: none after response_model exemption.
- Carried forward: 11.10 provenance; 11.13 full message routes + SQL conversation.

## Phase 11 — API contracts (11.8 production SQL app wiring)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_production_app_wiring.py -q --no-cov` (red then green)
  - `pytest tests/api -q --no-cov`
  - `make lint`
- Observed result:
  - Module `career_assistant.main:app` exposes SqlCvStore + SqlRoleStore.
  - `create_app()` without injection still uses in-memory stores for hermetic API
    tests (51 API tests green).
- Decisions made: `create_production_app` + `build_sql_stores` for the process
  entrypoint; keep `create_app` hermetic for test factories. Engine is lazy until
  first request.
- Problems hit: none.
- Carried forward: 11.9 SSE answer stream.

## Phase 11 — API contracts (11.8 durable drafts on SqlRoleStore)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/integration/test_sql_role_store.py::test_cover_letter_and_bullets_persist_across_store_instances -m integration`
  - `pytest tests/integration/test_sql_role_store.py tests/integration/test_draft_persistence.py -m integration`
  - `pytest tests/api/ -q --no-cov`
  - `ruff` / `mypy`
- Observed result:
  - Cover letter and bullets persist in `generated_drafts` and reload via a fresh
    SqlRoleStore instance and HTTP list.
  - Routes reconstruct CoverLetterDraftWire / BulletDraftWire from
    GeneratedDraftRecord JSON bodies.
- Decisions made: draft body stores structured JSON; citations taken from paragraph/
  bullet spanIds; hermetic InMemoryRoleStore unchanged.
- Problems hit: none after green.
- Carried forward: production SQL create_app default; 11.9 SSE.

## Phase 11 — API contracts (11.8 SqlRoleStore delete/reanalyse)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/integration/test_sql_role_store.py -m integration -q --no-cov`
  - `pytest tests/api/ -q --no-cov`
  - `pytest tests/integration/test_analysis_persistence.py -m integration -q --no-cov`
  - `ruff` / `mypy` on changed persistence modules
- Observed result:
  - delete removes role (cascade) and JD document; get returns None.
  - reanalyse bumps analysis_version, publishes new hermetic results, new job id.
  - list_mappings scoped to current analysis_version.
  - HTTP delete/reanalyse against injected SQL stores green (4 SqlRoleStore tests).
- Decisions made: JD document deleted after role (RESTRICT FK); drafts still
  process-memory on SqlRoleStore.
- Problems hit: none after green.
- Carried forward: durable drafts; production SQL create_app default; 11.9 SSE.

## Phase 11 — API contracts (11.8 SqlRoleStore)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/integration/test_sql_role_store.py -m integration -q --no-cov`
  - `pytest tests/api/ -q --no-cov`
  - `pytest tests/integration/test_analysis_persistence.py
    tests/integration/test_draft_persistence.py … -m integration`
  - `ruff` / `mypy` on role_store
- Observed result:
  - SqlRoleStore create publishes hermetic analysis into PostgreSQL; role ready,
    job succeeded; require_analysis reloads requirements/mappings/score.
  - HTTP create role + requirements work with injected SqlCvStore + SqlRoleStore.
  - Migration `a1b2c3d4e5f6` adds `roles.company`.
- Decisions made: claim/requirement spans from hermetic extractors are ensured in
  the spans table before publish; drafts remain process-memory on SqlRoleStore for
  now; create_app still defaults to in-memory stores.
- Problems hit: none after green.
- Carried forward: SQL delete/reanalyse; durable drafts; production SQL default;
  11.9 SSE.

## Phase 11 — API contracts (11.8 SqlCvStore)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/integration/test_sql_cv_store.py tests/integration/test_cv_http_sql.py -m integration -q --no-cov`
  - `pytest tests/api/ -q --no-cov`
  - `ruff` / `mypy` on `adapters/persistence/cv_store.py`
- Observed result:
  - SqlCvStore upload/get/span/delete round-trip via CvStore port against
    `TEST_DATABASE_URL`.
  - `create_app(cv_store=SqlCvStore(...))` serves CV + span HTTP routes from Postgres.
  - Hermetic API suite still green on InMemoryCvStore default.
- Decisions made: keep in-memory as create_app default for hermetic tests; inject
  SqlCvStore for SQL-backed runs. Roles/analysis SQL wiring deferred.
- Problems hit: none after green.
- Carried forward: SqlRoleStore / analysis persistence behind API; 11.9 SSE.

## Phase 11 — API contracts (11.8 hermetic lifecycle + draft list)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_role_lifecycle_routes.py -q --no-cov` (red then green)
  - `pytest tests/api/ -q --no-cov` → 51 passed
  - `ruff check` / `mypy` on changed modules
- Observed result:
  - DELETE role → 204 and subsequent get → `role_not_found`.
  - POST reanalyse → 202 with new succeeded job; role stays `ready`.
  - `analysis_incomplete` 409 when store marks role analysing.
  - Cover letters persisted and listed; bullets/cover-letter markdown export works.
- Decisions made: hermetic reanalyse remains synchronous; `mark_incomplete` is a
  store test helper, not an HTTP route.
- Problems hit: none after green.
- Carried forward: SQL-backed CV/role/analysis/draft persistence; 11.9 SSE.

## Phase 11 — API contracts (11.8 hermetic analysis artefacts)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_role_analysis_routes.py tests/api/test_role_routes.py -q --no-cov`
  - `ruff check` / `ruff format` on changed analysis modules
- Observed result:
  - Role create now runs hermetic rules extract→map→score synchronously; status
    `ready`, job `succeeded`.
  - Requirements, breakdown, gap-plan, interview-pack, bullets, cover-letter (or
    `insufficient_matched_requirements`), markdown export, ranking and compare
    routes pass the focused API suite (7 analysis + role tests).
- Decisions made: keep in-memory stores for hermetic API contracts; domain
  generation helpers remain the source of gap/interview/draft text; drafts stamp
  hermetic provenance with `leftMachine: false`.
- Problems hit: focused pytest hit the global 80% coverage gate — use `--no-cov`
  for slice runs; suite-wide coverage still via full `pytest`.
- Carried forward: SQL-backed CV/role/analysis persistence; generated cover-letter
  list; SSE ask (11.9); OpenAPI/frontend type agreement (11.11).

## Phase 11 — API contracts (11.8 partial: CV, spans, roles, jobs)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_cv_routes.py tests/api/test_span_routes.py tests/api/test_role_routes.py -q --no-cov`
  - `pytest tests/api/ -q --no-cov`, `pytest -q`, `ruff`, `mypy`
- Observed result:
  - CV paste upload/get/delete with intake error mapping.
  - Span evidence includes `spanId`; unknown span → `span_not_found`.
  - Role create requires CV (`cv_required`); returns 202 with queued job; list/get work.
- Decisions made: hermetic in-memory CV/role stores for API contract tests; SQL UoW
  wiring and analysis worker execution deferred. Multipart CV upload deferred.
- Problems hit: none material after response_model union/204 guard update.
- Carried forward: gap/interview/drafts/export/ranking/compare; durable persistence.

## Phase 11 — API contracts (11.3 upload limit, 11.7 providers)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_upload_size_limit.py -q --no-cov`
  - `pytest tests/api/test_provider_routes.py -q --no-cov`
  - `pytest tests/api/ -q --no-cov`, `pytest -q`, `ruff`, `mypy`
- Observed result:
  - ASGI Content-Length gate returns 413 `document_too_large` without calling `receive()`.
  - Provider catalogue reports availability/reasons; PUT enforces `egress_not_acknowledged`
    and `egress_not_permitted`; API keys absent from response bodies.
- Decisions made: workspace provider choice is process-memory for this slice
  (keyed by workspace cookie); SQL `provider_settings` wiring follows with CV/role
  persistence routes. Ollama listed available without a live reachability probe.
- Problems hit: FastAPI `list[Model]` response models broke the issubclass guard;
  renamed API provider test module to avoid colliding with `tests/unit/test_providers.py`.
- Carried forward: 11.8+ feature routes; durable provider_settings persistence.

## Phase 11 — API contracts (foundation: 11.1, 11.2, 11.4–11.6)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/ -q --no-cov`
  - `pytest tests/unit/test_persistence_boundary.py -q --no-cov`
  - `pytest -q`, `ruff`, `mypy`
- Observed result:
  - `ApiModel` serialises snake_case → camelCase; every route declares `response_model`.
  - `workspace` cookie issued HttpOnly / SameSite=Lax; invalid values replaced.
  - `X-Correlation-Id` echoed or minted on every response.
  - Error envelope `{error:{code,message,correlationId}}`; unhandled exceptions do not
    leak paths or provider payloads.
  - `GET /api/ready` returns provider/database/migration status; 503 when unhealthy.
- Decisions made: SQL readiness probe lives in `adapters/persistence/readiness.py`;
  HTTP package keeps the protocol only. Upload size rejection (11.3) waits for CV
  routes.
- Problems hit: FastAPI 0.141 nests routes under `_IncludedRouter` — tests walk
  `original_router`.
- Carried forward: 11.3, 11.7–11.13 feature and message routes.

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
