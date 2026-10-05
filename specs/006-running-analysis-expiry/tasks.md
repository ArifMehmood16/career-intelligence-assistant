# Tasks — running analysis expiry

Root PLAN/BACKLOG: 19.3. Execute sequentially; source work is isolated from the
human's running checkout. No project initialization or new dependencies needed.

## Scope and prerequisites

- [x] T001 Inspect worker/domain/progress/provider/UI implementation and read-only
  metadata; create spec/design artifacts in specs/006-running-analysis-expiry/.
- [x] T002 Analyze spec/plan/tasks against constitution before source edits.

## US1 — visible expiry (P1)

- [ ] T003 [US1] Add a red synthetic blocked-provider SQL regression in
  backend/tests/integration/test_analysis_worker_http_sql.py (FR-001, FR-005).
- [ ] T004 [US1] Reuse runtime recovery and locked terminal failure guards in
  backend/src/career_assistant/adapters/persistence/analysis_worker.py; update safe
  timeout wording in domain/jobs.py. Test fresh/completed/deleted races (FR-002).
- [ ] T005 [US1] Add retry-cancellation regression and implementation in existing
  provider resilience test/module; verify late successful response cannot publish
  in the SQL regression (FR-003).
- [ ] T006 [US1] Run focused backend checks and commit the green lifecycle fix.

## US2 — honest batch progress (P2)

- [ ] T007 [US2] Add component regressions for running judge/recheck guidance and
  terminal stale task state in frontend/src/components/role/AnalysisProgress.test.tsx.
- [ ] T008 [US2] Add guidance and terminal glyph normalization in AnalysisProgress.tsx;
  run frontend lint/typechecks/focused tests and commit (FR-004).

## Verification and documentation

- [ ] T009 Run make lint, make test and disposable make test-integration; inspect
  complete branch diff for scope, privacy and complexity (FR-005; SC-001/002).
- [ ] T010 Update README.md, PLAN.md, BACKLOG.md, docs/running-locally.md,
  docs/engineering-journal.md and AI_DEVELOPMENT_LOG.md with observed evidence
  and cancellation limits; record checkpoint without closing Phase 19 (SC-003).

## Dependencies and delivery

T001 → T002 → T003 → T004 → T005 → T006; T007 → T008; both → T009 → T010.
Backend and UI are independently testable; no parallel agents requested. Red tests
precede each production behavior; every commit passes its relevant checks. No
publish/merge action is required to establish the local repair checkpoint.
