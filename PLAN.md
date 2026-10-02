# Delivery plan — one career intelligence pipeline

Updated 2026-10-02. This plan replaces the competing v1 release/evaluation and v2
build tracks. BACKLOG.md lists priority; this file defines milestone acceptance.
Completed implementation history remains in AI_DEVELOPMENT_LOG.md and dated
evaluation rows.

**Checkpoint:** 19.1–19.3 implementation is committed for review. The human asked
to defer tests/lint and stop after documentation, commits and push. Their final
verification, migrations and 19.4 measurements remain open; no release gate is
claimed passed.

## Using Spec Kit for the existing project

GitHub Spec Kit v1.0.13 is adopted as a planning layer; see
[docs/spec-kit.md](docs/spec-kit.md). Each feature spec elaborates one bounded change
and links to this plan. Its plan/tasks do not replace this roadmap or close a gate.
The suggested first slice is the synthetic measurement work in 19.4. Adoption does
not execute that slice, apply migrations or resume deferred tests/lint.

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

- [ ] Delete the v1 extractors, span classifier, assessor/adjudicator, matching
      thresholds and production pipeline switch. Keep shared citation and draft
      value types only where current functionality consumes them.
- [ ] Replace legacy result reads in ranking, preparation, drafts, Ask and MCP with
      projections of validated chunks/verdicts and the published current score.
      A projection must never recalculate fit with retired rules.
- [ ] Ship one frontend analysis path; remove dead legacy components and queries.
- [ ] Provide a forward migration that removes retired storage and invalidates old
      analyses for reanalysis. Original uploads and current results survive.
      Define and test migration behavior without migrating a personal database.

Exit: no selectable or executable v1 analysis remains; synthetic upload, fit,
citations and generated-artifact flows still work; schema/deletion tests pass.

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

- [ ] Run one synthetic end-to-end browser journey: upload CV, add role, wait, inspect
      fit and source citation, prepare, draft and ask. Fix broken current features.
- [ ] Measure the current one-call/judge architecture on frozen synthetic labels.
      Record provider/model/prompt versions, physical calls, cold/warm duration,
      unsupported matches and ranking agreement in docs/evaluation.md. Tune on
      development data only. Hosted measurements need enabled keys and synthetic
      data; no paid or live quality claims from fixture tests.
- [ ] Verify the retirement/progress migration on disposable PostgreSQL and run the
      Supabase image CI row. Complete privacy/deletion and dependency/security checks.
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
