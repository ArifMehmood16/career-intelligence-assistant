# Tasks: Synthetic release verification

Root: [PLAN 19.4](../../PLAN.md#194--prove-the-current-product),
[BACKLOG Now](../../BACKLOG.md#now--prove-the-current-product).
Same branch/PR #48 by human instruction. No new application or v1 path.

## Setup

- [x] T001 Inspect current code, synthetic fixtures, tools and remaining gates in specs/011-synthetic-release-verification/research.md (FR-001).
- [x] T002 Complete linked design/task artifacts in specs/011-synthetic-release-verification/ and run read-only consistency analysis (FR-001/FR-007).

## Foundation

- [x] T003 Save already observed offline report with source/input/model provenance in docs/evaluation-results/ and docs/evaluation.md; tick only its PLAN.md checkbox (FR-004/SC-004).
- [x] T004 Repair advisory-reported dependencies in backend/pyproject.toml, both backend locks and frontend/bun.lock; preserve and synchronize frontend/package-lock.json by human instruction; verify compatibility (FR-006/SC-005).

## US1 — Complete the browser journey

Independent acceptance: one real browser/proxy/SQL/worker journey, synthetic data,
zero paid calls, persisted cited outputs and cleanup of its own workspace.

- [x] T005 [US1] Write a failing content-submission regression in frontend/src/components/workspace/AddRoleDialog.test.tsx for the job-file control (FR-003).
- [x] T006 [US1] Repair text-file reading/error state in frontend/src/components/workspace/AddRoleDialog.tsx; explicitly restrict to supported text files and record binary limitation in docs/how-to-use.md (FR-003).
- [x] T007 [US1] Add Bun-managed test-only Playwright runner/config and isolated production-wiring server setup in e2e/; require a loopback database ending _e2e and refuse existing servers (FR-002).
- [x] T008 [US1] Implement the CV/role/Fit/evidence/Prepare/draft/Ask/reload journey in e2e/tests/candidate-journey.spec.ts (FR-002/SC-001).
- [x] T009 [US1] Run the journey and fix demonstrated defects with focused regressions in their existing modules; record results in docs/engineering-journal.md (SC-001/SC-005).

## US2 — Fresh private startup

Independent acceptance: fresh isolated DB migrates before API readiness; packaged
runtime contains required TOML/source/migration resources; browser uses migrated SQL.

- [x] T010 [US2] Demonstrate current image resource failure and add migration-before-server regression in backend/tests/unit/test_serve.py (FR-003/SC-002).
- [x] T011 [US2] Repair root build context/resources in backend/Dockerfile, compose.yaml and .dockerignore; add migration-first entry point in backend/src/career_assistant/adapters/persistence/startup.py (FR-003).
- [x] T012 [US2] Build/run fresh isolated private services; observe readiness, analysis and shutdown; update docs/running-locally.md and docs/architecture.md (SC-002).

## US3 — Honest release evidence

Independent acceptance: safe reproducible reports, populated SQL preservation and
triaged scans, no fixture-time or historical-model claims as current quality.

- [x] T013 [US3] Add populated c1 -> b2 upgrade preservation/default/constraint test in backend/tests/integration/test_call_progress_migration.py using raw historical columns and finally restore head (FR-005/SC-003).
- [x] T014 [US3] Run new migration test and full SQL suite on disposable TEST_DATABASE_URL; record exact evidence in docs/engineering-journal.md (SC-003).
- [x] T015 [US3] Freeze explicitly current synthetic expectations in sample-data/evaluation/ before model execution; document development-only scope in docs/evaluation.md (FR-004).
- [x] T016 [US3] Extend only existing benchmark/report code under backend/src/career_assistant/ops/ where required to record unsupported matches/ranking agreement, with focused tests in backend/tests/ (FR-004/SC-004).
- [ ] T017 [US3] Run available local Ollama models using shipped synthetic fixtures and explicit closed hosted gate; save safe model/prompt/input/call/duration/quality provenance in docs/evaluation-results/ (FR-004/SC-004).
- [x] T018 [US3] Run dependency/source/redacted tracked-file secret scans; narrowly triage findings and repair actionable defects in existing modules, record scoped results in docs/threat-model.md and docs/engineering-journal.md (FR-006/SC-005).

## Checkpoint

- [ ] T019 Run full lint/unit/SQL/browser checks via Makefile and inspect complete branch diff; no weakened tests or unrelated changes (SC-005).
- [ ] T020 Update current docs/PLAN.md/BACKLOG.md and AI_DEVELOPMENT_LOG.md from observed checks only; keep README.md product-focused (FR-007).
- [ ] T021 Commit reviewable passing steps, push existing branch and update PR #48; observe its updated-head CI without merging (FR-001/SC-005).

## Dependencies and execution

T001–T004 precede dependent implementation. US1 and US2 use separate files but
startup proof must precede complete journey acceptance. US3 populated-migration
work can use the same disposable engine after startup; local measurements depend
on frozen labels and observed fixture reports. Security and the final checks cover
all resulting changes. Work sequentially in this checkout; no extra agent needed.

Parallel opportunities: read-only dependency and source scans can run together;
US1 component checks and US2 image build are independent after dependency repairs;
SQL preservation and offline report inspection are independent reads. No concurrent
edits to shared docs, locks or Git state.

Deliver the offline evidence first, then each passing regression/fix increment.
No fresh scaffolding beyond the missing test runner. Open tasks remain unchecked;
failed/incomplete model runs are reported honestly and never publish invented scores.
