# Delivery plan — one career intelligence pipeline

Updated 2026-10-07 after reviewing the remaining work against code, tests and
merged history. BACKLOG.md owns priority; this file owns milestone acceptance.
Historical delivery details remain in AI_DEVELOPMENT_LOG.md and the engineering journal.

**Current checkpoint:** 19.1 retirement and 19.2–19.3 provider/runtime acceptance
are verified. Existing implementations were reused; spec 010 adds the missing
parser lifecycle and actual thread cancellation/accounting regressions. Local
`make lint` and `make test` pass (825 backend / 192 frontend, three existing skips).
No personal database, paid provider call or new dependency was used.

[PR #46](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/46)
and [PR #47](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/47)
are merged. Main was synchronized at `6340cd0` before the sole current task branch,
`test/phase-19-runtime-verification`, was created. The final PR #47 code head
`7ff3ac4` passed lint/hermetic, PostgreSQL 16 and Supabase Postgres 17 in
[CI run 37532319038](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37532319038).
Updated-head CI remains enforced; the human owns merging.

**Next genuine work: 19.4.** The benchmark exists and its tests pass, but the
command remains unexecuted. A full synthetic browser journey, frozen-label model
quality/latency evaluation, populated progress-migration preservation,
dependency/security checks and one reproducible startup path remain open.
The duplicate browser smoke request is consolidated below. Retired v1 comparison
and repeated implementation of verified provider/concurrency features are superseded.
No live quality improvement is inferred from passing fixture checks.

## Using Spec Kit for the existing project

GitHub Spec Kit v1.0.13 is the bounded development workflow; see
[docs/spec-kit.md](docs/spec-kit.md). Feature specs elaborate a root item rather
than replacing this roadmap. Completed records are historical; measured results
belong in docs/evaluation.md. The current
[runtime verification record](specs/010-runtime-verification/spec.md) reconciles
19.2–19.3 acceptance. The
[benchmark record](specs/001-synthetic-analysis-benchmark/spec.md) describes the
existing tooling; execution and quality evidence remain distinct gates.

## Approved direction

The human requested immediate v1 retirement, provider-specific execution, fewer
model calls, bounded parallel I/O, CPU multiprocessing, and visible remaining time
and calls. This supersedes the old 18.14-before-18.15 gate. Retirement does not imply
that current model quality has been measured or that the old quality gate passed.

One modular monolith, one analysis: stored text → validated chunks/requirements →
hybrid evidence search → validated judge verdicts → domain arithmetic. Fit, Gaps,
Prepare, Letter, ranking, Ask and MCP consume those same stored results. Provider
modules adapt Ollama, OpenAI and Anthropic; the application reads capabilities and
execution policy. Hosted egress remains opt-in. No personal documents are used in
hosted development checks.

## 19.1 — retire the competing analysis

- [x] Show earned points and full-credit shortfall for each requirement using stored
      publication weights; green/red arrows with labels, null distinct from zero,
      and filter-preserving API/component/SQL/Browser checks (spec 008).

- [x] Add combined requirement status/score filters with counts, clear/reset and
      null-score handling; refresh current architecture diagrams and synthetic
      screenshots. Component/browser checks preserve overall fit and evidence.
- [x] Delete the v1 extractors, span classifier, assessor/adjudicator, matching
      thresholds and production pipeline switch. Keep shared citation and draft
      value types only where current functionality consumes them.
- [x] Replace legacy result reads in ranking, preparation, drafts, Ask and MCP with
      projections of validated chunks/verdicts and the published current score.
      A projection must never recalculate fit with retired rules.
- [x] Ship one frontend analysis path; remove dead legacy components and queries.
- [x] Provide a forward migration that removes retired storage and invalidates old
      analyses for reanalysis. Original uploads and current results survive.
      Define and test migration behavior without migrating a personal database.

Exit: no selectable or executable v1 analysis remains; synthetic upload, fit,
citations and generated-artifact flows still work; schema/deletion tests pass.

Evidence (2026-10-06, delivery reconciled 2026-10-07):
[spec 009](specs/009-retirement-verification/spec.md) proves populated historical
upgrades, legacy live-job termination, original/current row preservation,
selector/schema rejection, uniform consumers/citations/artifacts,
invalidation/reanalysis and scoped deletion. Combined local checks after including
PR #46 passed 818 backend / 192 frontend and all 149 disposable SQL tests.
PR #47 is merged at `6340cd0`; its final three-job CI passed on `7ff3ac4`.
Already-applied retirement revisions cannot recover erased legacy job identities;
the correction protects upgrades that still cross that revision.

The diagrams, usage guide and ten synthetic gallery screenshots describe current
behavior, including point contributions, contextual judgments and Ask processing.
Component/gallery checks do not close the full browser journey or model-quality gate.

## 19.2 — reduce model/API calls and respect each provider

- [x] Assess verified qualitative experience and seniority using overall CV/JD
      context in existing judge calls; retain scoped numeric years, evidence caps,
      context-aware cache/budget checks and asked/supported explanations (spec 008).
      These regressions prove behavior, not measured model quality.

- [x] Read each fitting document with one structured response containing line-range
      chunks, details, atomic requirements and technology relationships. Validate
      coverage and verbatim fields before storage; bounded repairs/splits handle
      malformed/truncated results. Never trim evidence to force a successful call.
- [x] Pack judge requirements against both input and output capacity. Use configured
      per-model operational budgets; remove a shared small output ceiling. Batch
      corrective judging of changed candidate packets; unchanged candidates cost no
      extra judge call. Cache reusable verdicts.
- [x] Batch Ollama and OpenAI embeddings. Reused chunks and vectors make no probe
      call when the adapter supplies model identity/dimensions. Simultaneous roles
      share one CV index within the process.
- [x] Keep separate provider adapters and execution profiles. Context/output limits,
      concurrency and schema/temperature support are model configuration; an Ollama
      operator may tune local concurrency. Hosted rate headers bound shared calls.

Exit: contract tests cover one-call documents, large output budgets, batched repairs,
cache reuse and native embeddings; no hosted content leaves through a new path.

Evidence (2026-10-07): [spec 010](specs/010-runtime-verification/spec.md).
185 focused provider tests pass: one-response coverage/repair/split checks,
large-capacity judge/cache/corrective retrieval, native Ollama/OpenAI embedding
contracts, shared CV reuse, execution profiles, schema dialects, safe OpenAI
failures and local/hosted shared call gates. Full local lint/hermetic checks pass.
These use recorded/fake provider boundaries; live quality stays open under 19.4.

## 19.3 — bounded concurrency and useful progress

- [x] Show Ask processing before any response, answering and history refresh;
      clear status on success/failure/stop and protect a new request against late
      events from a stopped one. Deferred-response regressions pass (spec 008).

- [x] Enforce the existing running-job expiry during operation; preserve terminal
      state against late provider failures/responses, stop subsequent retries and
      explain batch-completion counts. Synthetic blocked-call, publication-race,
      cancellation and component regressions pass, with full local checks.

- [x] Overlap independent document reads and judge batches with bounded threads;
      preserve call-accounting/cancellation context across threads. Dependencies,
      validation and publication remain ordered.
- [x] Parse binary documents in a bounded spawned CPU process pool, separate from
      model/database I/O; plain text avoids startup overhead. Stop workers on
      shutdown/timeout. Pass immutable upload data, never database connections or
      provider objects. Spawned children inherit the host environment; they are not
      a credential sandbox (see docs/threat-model.md).
- [x] Show estimated time and remaining LLM/embedding API calls. Track physical
      attempts, including retries; cached/skipped work consumes zero calls. Label
      undiscovered work and repair uncertainty. Parallel-stage ETA follows overlap;
      no timing history means unknown time, never a fabricated promise.

Exit: focused concurrency, failure, retry-accounting and component checks pass;
full lint/unit checks and PostgreSQL integration checks pass or state their concrete
external blocker. Document verification and measured latency separately.

Evidence (2026-10-07): [spec 010](specs/010-runtime-verification/spec.md).
55 focused runtime tests pass, including real spawned-worker timeout/crash
termination, pool recreation, idempotent close, both app lifespan paths and actual
thread cancellation/progress/retry accounting. Existing tests retain ordered
repairs, bounded overlap, cache/skipped work, unknown ETA and parallel-stage ETA.
Full lint and 825 backend / 192 frontend checks pass; frontend progress components
cover simultaneous stages and incomplete estimates. The unchanged 149 SQL
contracts passed locally for spec 009 and on both final PR #47 database CI jobs;
updated-head CI is still required. No model-latency measurement is claimed.

## 19.4 — prove the current product

Measurement tooling checkpoint: `make benchmark` drives the current analysis with
named synthetic fixtures, cold/warm application caches, physical request accounting
and attribution. Explicit live mode reuses provider factories and the egress gate.
This is fixture retrieval; PostgreSQL/browser latency and frozen-label quality
evaluation are separate work. No benchmark result is claimed before execution.

- [ ] Implement and run one reusable synthetic Playwright journey: upload CV, add
      role, wait, inspect fit/source citation, prepare, draft and ask. Fix broken
      current features. This also satisfies the former duplicate browser-smoke task.
- [ ] Execute the existing offline synthetic benchmark and record timing/accounting
      provenance in docs/evaluation.md. Fixture timing proves neither model quality
      nor SQL/browser latency; no paid provider request is needed.
- [ ] Measure the current one-call/judge architecture on frozen synthetic labels.
      Record provider/model/prompt versions, physical calls, cold/warm duration,
      unsupported matches and ranking agreement in docs/evaluation.md. Tune on
      development data only. Hosted measurements need enabled keys and synthetic
      data; no paid or live quality claims from fixture tests.
- [x] Repair PR #43's observed collection/lint failures and pass local lint,
      hermetic and disposable PostgreSQL regression/migration-cycle checks.
      Enable CI on PR updates/reopening. See specs/005-pr43-ci-repair/.
- [x] Observe both database image jobs and lint/hermetic CI on code head `5b8a585`
      ([run](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37293311548)); keep updated-head checks enforced.
- [ ] Prove populated progress-migration preservation. Empty migration cycles and
      retirement preservation/deletion already pass; do not repeat them as new work.
- [ ] Complete dependency/security release checks. Stored-data deletion is verified
      under 19.1 and is not a full security audit.
- [ ] Prove one startup/deployment path. Repair Docker configuration or remove its
      supported claim. Keep deployment private until authentication exists.

Exit: observed results, reproducible startup and one complete current journey. An
architecture checkpoint is distinct from this measured release gate.

## Scope limits

One CV per workspace; candidate use only; English text PDF/DOCX/plain text;
no OCR, multi-user auth, auto-apply, job-board ingestion, distributed queue, or
model-emitted fit score. Supporting letters remain narrative-only for scoring.
Do not rebuild retired approaches to satisfy old tests or measurement plans.
