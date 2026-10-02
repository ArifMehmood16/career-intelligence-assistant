# Tasks: Display published recency gaps

Input: [spec](spec.md), [plan](plan.md). Root: PLAN 19.1, verification under 19.4.

## Setup

- [x] T001 Inspect source/tests and diagnose live response using paths/types only.
- [x] T002 Specify/plan/analyze bounded change; no scoring or architectural change.

## US1 — Published Fit and Gaps

Independent criterion: recency response accepted by client and renders both panes
with a percentage weighting factor; unknown categories remain invalid.

- [x] T003 [US1] Author synthetic recency fixture and regressions in frontend/src/api/verdicts.test.ts, components/role/verdicts/RoleFitContainer.test.tsx and TraceDrawer.test.tsx; do not run suites.
- [x] T004 [US1] Align frontend/src/api/schemas.ts and types/index.ts gap dimensions with domain.
- [x] T005 [US1] Render recency percentage in frontend/src/components/role/verdicts/VerdictGapsPanel.tsx; add routes/dev.states.tsx example.
- [x] T006 [US1] Repeat safe live schema/read diagnosis of already-published data; no analysis/model calls.

## Checkpoint

- [x] T007 Update docs/api-contract.md, features.md, PLAN/BACKLOG, AI log and journal; source/diff review, formatting and local commit.
- [ ] T008 Execute focused/full tests, lint/typecheck/security and release checks only after human lifts deferral.

Dependency order: T001–T002 → T003 → T004–T005 → T006–T007; T008 deferred.
API and presentational authoring are independent file work but this task uses one
agent sequentially. Incremental strategy: client acceptance, correct rendering,
documentation, deferred verification. Authored regression means no red/green proof.
