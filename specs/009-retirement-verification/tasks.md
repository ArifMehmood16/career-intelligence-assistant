# Tasks: Retirement verification

**Input**: [spec.md](spec.md), [plan.md](plan.md), research/data-model/contracts/quickstart.
**Root**: PLAN 19.1. Tests required by spec and AGENTS.md.

## Phase 1: Setup

- [x] T001 Inspect existing retirement and consumer implementation and create bounded specs/009-retirement-verification/spec.md on a branch from current main.
- [x] T002 Research disposable migration strategy and legacy job lifecycle in specs/009-retirement-verification/research.md.

## Phase 2: Foundation

- [x] T003 Run Spec Kit prerequisite and read-only consistency checks for specs/009-retirement-verification/{spec,plan,tasks}.md before implementation.

## Phase 3: US1 — preserve uploads and current results

Independent test: populated historical schema upgraded to head preserves originals/current publications and erases retired scores/drafts only.

- [x] T004 [US1] Add populated preservation and historical live-job regressions in backend/tests/integration/test_retirement_preservation.py and scoped seed helpers in backend/tests/support/retirement_seed.py (FR-001/002/003/008, SC-001/002).
- [x] T005 [US1] Demonstrate legacy queued/running jobs remain live; repair backend/migrations/versions/c4e8a1d7b902_retire_legacy_analysis.py with terminalization before pipeline identity removal, preserving current jobs and valid publications (FR-003).
- [x] T006 [US1] Run focused integration/unit/mypy/Ruff gates and commit green migration changes; document applied-migration limitation in specs/009-retirement-verification/research.md.

## Phase 4: US2 — one publication everywhere

Independent test: one SQL-backed synthetic analysis, stored score compared with every consumer, citations opened, drafts generated, invalidation excludes all result consumers.

- [x] T007 [US2] Add consistency, citation/artifact and invalidation regressions in backend/tests/integration/test_publication_consumers.py, reusing backend/tests/support/v2_http.py (FR-004/005/008, SC-003).
- [x] T008 [US2] Exercise reanalysis and Ask/MCP publication projections using backend/tests/integration/test_publication_consumers.py and existing persistence/API tests, correcting only demonstrated defects in backend/src/career_assistant/ (FR-004/005).
- [x] T009 [US2] Run focused checks and commit green consumer regressions for backend/tests/integration/test_publication_consumers.py.

## Phase 5: US3 — permanent retirement and scoped deletion

Independent test: selector/worker/schema guards reject retired execution; populated deletion removes all scoped rows while another workspace remains intact.

- [x] T010 [US3] Verify worker selection, retired-schema guards and sole frontend path in backend/tests/unit/test_current_analysis_worker.py, backend/tests/integration/test_retirement_preservation.py and frontend/src/ (FR-006).
- [x] T011 [US3] Add populated workspace-deletion regression in backend/tests/integration/test_publication_consumers.py covering originals, current/operational tables and unaffected second workspace (FR-007/008, SC-004).

## Phase 6: Validation and checkpoint

- [x] T012 Run make lint, make test and disposable make test-integration; inspect full branch diff, security/design findings and record evidence in docs/engineering-journal.md.
- [x] T013 Update README.md, PLAN.md, BACKLOG.md, docs/production-wiring.md and AI_DEVELOPMENT_LOG.md only for proven retirement acceptance and observed evidence.
- [x] T014 Push green commits, create/attach review PR, inspect all three final-head CI jobs and record delivery in docs/engineering-journal.md. Do not merge.

## Dependencies and parallel opportunities

T001 → T002 → T003 precedes implementation. T004 → T005 → T006, then T007 → T008 → T009. T010/T011 → T012 → T013 → T014. US1 and US2 files can be drafted independently but migration/SQL tests must run serially against the dedicated database. US3 reuses US2 fixtures, so follows them. No parallel SQL invocation.

## Implementation strategy

US1 is the first deliverable and has a demonstrated defect candidate. Commit each green slice, retain shared value types, then extend consumer and deletion coverage. Full phase closure follows all evidence; later provider/concurrency/browser/measurement gates remain open.

## Delivery evidence

PR #47 is open and attached. CI run 37527404818 passed all three jobs on 3511aa9.
The final documentation checkpoint receives its own head CI before the task report.
Local test counts and concrete red/green evidence are in docs/engineering-journal.md.
