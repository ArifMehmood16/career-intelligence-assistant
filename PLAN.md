# Delivery plan — one career intelligence pipeline

Updated 2026-10-05. This plan replaces the competing v1 release/evaluation and v2
build tracks. BACKLOG.md lists priority; this file defines milestone acceptance.
Completed implementation history remains in AI_DEVELOPMENT_LOG.md and dated
evaluation rows.

**Checkpoint:** Phase 18 foundations, the 19.1–19.3 consolidation and subsequent
provider/display repairs are merged in [PR #42](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/42)
at `2212790`. Superseded task branches and the merged delivery branch are removed;
their complete history is preserved on `main`. The local main checkout is synced.
The human explicitly resumed verification to repair [PR #43](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/43).
Its original creation CI failed lint and test collection. The bounded
[CI repair](specs/005-pr43-ci-repair/spec.md) aligns current fixtures/contracts,
repairs response cancellation, evidence-deletion invalidation and citation labels,
and restores pgvector resolution across repeated migration cycles. Local
`make lint`, `make test` and `make test-integration` pass on synthetic data;
[GitHub CI](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37293311548) passed all three jobs
on code head `5b8a585`. CI now runs on synchronized and reopened PR heads. No personal database or paid model calls were used.

The synthetic benchmark is implemented but unexecuted. Phase 19.1 populated
retirement preservation and publication/deletion checks now pass. Browser journeys,
progress acceptance, security/dependency checks and measured quality/latency
gates remain open. Passing regression checks do not close those
broader acceptance criteria.

## Using Spec Kit for the existing project

GitHub Spec Kit v1.0.13 is adopted as a planning layer; see
[docs/spec-kit.md](docs/spec-kit.md). Each feature spec elaborates one bounded change
and links to this plan. Its plan/tasks do not replace this roadmap or close a gate.
The first scoped change is
[synthetic analysis benchmarking](specs/001-synthetic-analysis-benchmark/spec.md).
Its implementation and regression tests pass the local checks; benchmark runs
remain pending. Retirement preservation is verified by spec 009. Specification
quality review proves no application behavior.

The human-requested [OpenAI analysis repair](specs/002-openai-request-errors/spec.md)
addresses a reproduced advert-format rejection under 19.2. The repaired converter
received HTTP 200 with a tiny synthetic request; safe rejection diagnostics are
implemented. The human later reported a complete analysis, confirmed as a ready
publication by read-only HTTP. Its regression tests pass in the local suite;
the measured release gate remains pending.

The subsequent [incomplete-judging diagnosis](specs/003-judge-failure-diagnostics/spec.md)
adds content-free timeout/judge diagnostics under 19.2. Read-only timings suggest
three exhausted 60-second judge attempts; the local ignored limit is now 180 seconds.
The later completed analysis does not prove that timeout was the original cause;
regressions pass in the local suite; the release gate remains open.

The human subsequently reported a completed analysis; read-only HTTP confirms a
ready role and published verdicts. The [19.1 recency display repair](specs/004-recency-gap-display/spec.md)
aligns the frontend with the domain's existing fourth gap category, which the
client previously rejected. The same live result now passes client validation
through API and web proxy; synthetic gallery rendering was inspected. Local
suites pass; broader release/quality gates remain pending; no reanalysis or scoring change is needed.

Next checkpoint: verify Phase 19.2 provider efficiency and execution contracts,
then 19.3 concurrency/progress before 19.4 browser, security and measurement work.
Documentation follow-ups receive their own updated-head CI. Local disposable
PostgreSQL regression and migration-cycle checks pass; successful checks only
close the bounded acceptance they actually exercise.

PR #43 is merged at `8333b39`. The human-requested
[running-analysis expiry repair](specs/006-running-analysis-expiry/spec.md)
addresses the 20-minute spinner: the existing 15-minute timeout was enforced only
at startup. Runtime sweeps now fail expired jobs, preserve terminal outcomes and
stop subsequent retries; the UI explains batch completion and stops failed-task
animation. Local lint, 810 backend and 172 frontend tests, and all 141 disposable
PostgreSQL integration tests pass. The original provider wait remains unexplained;
this repair does not establish model quality or measured release latency.

The scoped [requirement filters and documentation](specs/007-requirement-filters-docs/spec.md)
add combined status/domain-score filtering without changing the publication.
Current system, pipeline and job-lifecycle diagrams reflect inspected code;
screenshots are refreshed synthetic component-gallery captures. Browser filter
interactions and component regressions pass. Work is consolidated in the normal
checkout; the merged documentation checkpoint branch has been removed. Broader
browser journeys and measured release gates stay open.

[PR #44](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/44)
is merged at `ad88781`. [CI run 37301152754](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37301152754)
passed lint/typecheck/hermetic, PostgreSQL 16 and Supabase Postgres 17 on `08ef56b`.
The merge preceded the final plan/log commit; the human requested another PR
for that remaining documentation. [PR #45](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/45)
is merged at `0362666`.

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

Evidence (2026-10-06): [retirement verification](specs/009-retirement-verification/spec.md)
adds populated historical upgrades, legacy live-job termination, original/current
row equality, selector/schema rejection, consumer consistency, source-citation and
artifact generation, invalidation/reanalysis and scoped hard-deletion checks.
`make lint`, `make test` (810 backend / 180 frontend) and all 149 disposable SQL tests
pass. Current frontend Fit/Gaps use `RoleFitContainer` and the verdict publication;
shared presentation values remain where used. No personal migration or paid call.
Already-applied retirement revisions cannot recover erased legacy job identities;
this correction protects upgrades that still cross that revision. Broader release
and measured model-quality gates remain open.

## 19.2 — reduce model/API calls and respect each provider

- [ ] Read each fitting document with one structured response containing line-range
      chunks, details, atomic requirements and technology relationships. Validate
      coverage and verbatim fields before storage; bounded repairs/splits handle
      malformed/truncated results. Never trim evidence to force a successful call.
- [ ] Pack judge requirements against both input and output capacity. Use configured
      per-model operational budgets; remove a shared small output ceiling. Batch
      corrective judging of changed candidate packets; unchanged candidates cost no
      extra judge call. Cache reusable verdicts.
- [ ] Batch Ollama and OpenAI embeddings. Reused chunks and vectors make no probe
      call when the adapter supplies model identity/dimensions. Simultaneous roles
      share one CV index within the process.
- [ ] Keep separate provider adapters and execution profiles. Context/output limits,
      concurrency and schema/temperature support are model configuration; an Ollama
      operator may tune local concurrency. Hosted rate headers bound shared calls.

Exit: contract tests cover one-call documents, large output budgets, batched repairs,
cache reuse and native embeddings; no hosted content leaves through a new path.

## 19.3 — bounded concurrency and useful progress

- [x] Enforce the existing running-job expiry during operation; preserve terminal
      state against late provider failures/responses, stop subsequent retries and
      explain batch-completion counts. Synthetic blocked-call, publication-race,
      cancellation and component regressions pass, with full local checks.

- [ ] Overlap independent document reads and judge batches with bounded threads;
      preserve call-accounting/cancellation context across threads. Dependencies,
      validation and publication remain ordered.
- [ ] Parse binary documents in a bounded spawned CPU process pool, separate from
      model/database I/O; plain text avoids startup overhead. Stop workers on
      shutdown/timeout. Pass immutable upload data, never database connections or
      provider objects. Spawned children inherit the host environment; they are not
      a credential sandbox (see docs/threat-model.md).
- [ ] Show estimated time and remaining LLM/embedding API calls. Track physical
      attempts, including retries; cached/skipped work consumes zero calls. Label
      undiscovered work and repair uncertainty. Parallel-stage ETA follows overlap;
      no timing history means unknown time, never a fabricated promise.

Exit: focused concurrency, failure, retry-accounting and component checks pass;
full lint/unit checks and PostgreSQL integration checks pass or state their concrete
external blocker. Document verification and measured latency separately.

## 19.4 — prove the current product

Measurement tooling checkpoint: `make benchmark` drives the current analysis with
named synthetic fixtures, cold/warm application caches, physical request accounting
and attribution. Explicit live mode reuses provider factories and the egress gate.
This is fixture retrieval; PostgreSQL/browser latency and frozen-label quality
evaluation are separate work. No benchmark result is claimed before execution.

- [ ] Run one synthetic end-to-end browser journey: upload CV, add role, wait, inspect
      fit and source citation, prepare, draft and ask. Fix broken current features.
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
- [ ] Complete broader progress migration preservation and dependency/security
      release checks; retirement preservation and stored-data deletion are verified
      under 19.1, without claiming a full security audit.
- [ ] Prove one startup/deployment path. Repair Docker configuration or remove its
      supported claim; add one Playwright smoke journey. Keep deployment private
      until authentication exists.

Exit: observed results, reproducible startup and one complete current journey. An
architecture checkpoint is distinct from this measured release gate.

## Scope limits

One CV per workspace; candidate use only; English text PDF/DOCX/plain text;
no OCR, multi-user auth, auto-apply, job-board ingestion, distributed queue, or
model-emitted fit score. Supporting letters remain narrative-only for scoring.
Do not rebuild retired approaches to satisfy old tests or measurement plans.
