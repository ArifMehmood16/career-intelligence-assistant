# Tasks: PR #43 CI repair

## Setup and foundations

- [x] T001 Inspect CI logs and reproduce collection/Ruff failures in backend/tests and backend/src.
- [x] T002 Record scope, validation override and design in specs/005-pr43-ci-repair/.

## US1 — Trust the reviewed change

- [x] T003 [US1] Align moved imports/current contracts in backend/tests/support and backend/tests/unit; correct integration helper imports in backend/tests/integration.
- [x] T004 [US1] Repair reported formatting/import checks in backend/src and backend/tests.
- [x] T005 [US1] Run make lint and make test; repair observed source/fixture defects in backend/src, backend/tests and frontend/src with focused regressions.
- [x] T006 [US1] Verify make test-integration on isolated PostgreSQL data and both database CI jobs in .github/workflows/ci.yml.

## US2 — Check the current review head

- [x] T007 [US2] Enable synchronized/reopened review checks in .github/workflows/ci.yml.
- [x] T008 [US2] Push existing PR branch, update description and inspect final-head CI results through gh.

## Delivery

- [x] T009 Update observed status and remaining release work in README.md, AGENTS.md, PLAN.md, BACKLOG.md, AI_DEVELOPMENT_LOG.md and docs/engineering-journal.md.

Dependencies: T001–T002 precede implementation; T003–T004 unblock T005/T006;
T007 precedes T008; T009 records observed outcomes. Independent opportunities:
formatter/source checks and frontend checks can run concurrently; database image
jobs already run in parallel. No agent delegation is needed. Deliver repairs in
focused commits, preserve tests and gates, then verify the published head.

Coverage: FR-001 T003–T006; FR-002/FR-003 T005–T006; FR-004 T007–T008;
FR-005 T008–T009; FR-006 T005–T006. SC-001 T005; SC-002 T006/T008;
SC-003 T005/T009 review.

Observed verification: make lint, make test (809 backend, 169 frontend) and all
135 disposable SQL tests pass. [CI run 37293311548](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37293311548) passed all three jobs
on code head 5b8a585. Documentation delivery is checked again on its published head;
no broader quality, browser or security gate is closed here.
