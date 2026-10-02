# Tasks: Synthetic analysis benchmark

Root: [PLAN 19.4](../../PLAN.md#194--prove-the-current-product). Checkmarks mean
implementation is present; validation stays pending until explicitly resumed.

## Phase 1 — Existing-project prerequisites

- [x] T001 Inspect current reader, indexer, matcher, provider factories/accounting,
  fixture manifest and governance; record reuse in `research.md` and `plan.md`.
- [x] T002 Author SQL naming regression in `backend/tests/unit/test_retirement_migration.py`
  and repair full-form constraint names in
  `backend/migrations/versions/c4e8a1d7b902_retire_legacy_analysis.py` (PLAN 19.1).

## Phase 2 — User Story 1: offline cold/warm measurement

- [x] T003 [US1] Author cold/warm, cache, failure and privacy regressions in
  `backend/tests/unit/test_analysis_benchmark.py`; do not execute them (FR-001–004,006–008).
- [x] T004 [US1] Load named shipped pairs with contained paths and SHA-256 fingerprints
  in `backend/src/career_assistant/ops/benchmark_cases.py` (FR-001,004).
- [x] T005 [US1] Implement a locked probe and measured fixture cache/index boundaries
  in `backend/src/career_assistant/ops/benchmark_probe.py` and `benchmark_runtime.py`
  (FR-002,003). Observation status is `succeeded`, `failed`, or `skipped`;
  failed/skipped scores are null, skipped elapsed time is null.
- [x] T006 [US1] Drive the current analysis with fresh cold caches and retained warm
  caches in `backend/src/career_assistant/ops/benchmark_runtime.py` (FR-002,008).
- [x] T007 [US1] Emit `analysis-benchmark-v1` JSON, per-case summaries, attribution,
  safe exit codes and exclusive output files in `backend/src/career_assistant/ops/benchmark.py`
  (FR-004,006,007). Repetitions are an integer in [1, 20].

## Phase 3 — User Story 2: explicit provider measurements

- [x] T008 [US2] Measure each physical transport request, including retries/failures
  and separate metadata calls in `backend/src/career_assistant/ops/benchmark_probe.py`
  (FR-003). Preserve progress/accounting task context as a distinct measure.
- [x] T009 [US2] Reuse factories, require live opt-in and disable fallback in
  `backend/src/career_assistant/ops/benchmark_runtime.py` and `benchmark.py`; author
  transport/egress regression coverage in `backend/tests/unit/test_analysis_benchmark.py`
  (FR-005,006,008).

## Phase 4 — Documentation and checkpoint

- [x] T010 Add the offline-safe Make target and update `Makefile`,
  `docs/evaluation.md`, `docs/running-locally.md`, `docs/threat-model.md`,
  `PLAN.md`, `BACKLOG.md`, `AI_DEVELOPMENT_LOG.md` and `docs/engineering-journal.md`.

## Phase 5 — Deferred verification

- [ ] T011 Execute focused pytest, Ruff/mypy and full quality checks; record observed
  results in `AI_DEVELOPMENT_LOG.md`. No red/green result is claimed before execution.
- [ ] T012 Run offline measurements, requested synthetic live measurements and
  disposable migration preservation checks; record observed results exclusively in
  `docs/evaluation.md` and `docs/engineering-journal.md`. No root gate closes early.

## Dependencies and implementation strategy

T001–T002 precede benchmark delivery. US1 provides the offline MVP; US2 extends its
probe/runtime after US1. T010 follows implementation. T011–T012 remain pending under
the human's instruction. Case loading and probe modules can be edited independently
after T003, but this session uses one agent and sequential implementation. No
project initialization, frontend work, provider redesign or new dependencies.
