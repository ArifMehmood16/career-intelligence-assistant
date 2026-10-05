# Tasks — requirement filters and documentation

- [x] T001 Inspect source/UI/tests and create linked scope/design in specs/007-requirement-filters-docs/.
- [x] T002 Analyze spec/design/tasks against constitution before implementation.
- [x] T003 [US1] Add red combined status/score, zero/null, empty/clear and fit-preservation tests in frontend/src/components/role/verdicts/VerdictsPanel.test.tsx.
- [x] T004 [US1] Implement RequirementsPanel.tsx, wire into VerdictsPanel.tsx, show the existing requirement percentage in VerdictCard.tsx; preserve order and trace callbacks.
- [x] T005 [US1] Cover synthetic filtered/empty gallery states in frontend/src/routes/dev.states.tsx and its test; run focused checks, frontend lint/typecheck and commit green.
- [x] T006 [US2] Update README.md and docs/architecture.md current Mermaid system, pipeline and job-lifecycle diagrams from inspected source.
- [x] T007 [US2] Verify filter interaction with Browser and save/inspect synthetic screenshots under docs/images; update docs/how-to-use.md provenance and instructions.
- [x] T008 Run make lint/test, inspect complete diff and update PLAN.md, BACKLOG.md, docs/features.md, docs/engineering-journal.md and AI_DEVELOPMENT_LOG.md with observed results.
- [x] T009 Commit/push green steps, create/update review PR, attach it and inspect CI. Verify one checkout and only main plus the active branch remain.

Delivery: PR #44 is merged at ad88781/attached; run 37301152754 passed all three
jobs on 08ef56b. The human requested a new PR for the checkpoint docs pushed
after the merge: PR #45 is open/attached. This documentation receives its own
PR-head CI. Broader release
acceptance remains in PLAN.md.

Dependencies: T001 → T002 → T003 → T004 → T005 → T007; T006 independent of UI;
T005/T006/T007 → T008 → T009. No agent delegation. FR-001 T003/T004; FR-002
T003/T005; FR-003 T003/T004; FR-004 T006/T007/T008; FR-005 T005/T009. All
requirements covered; no constitution conflicts or unresolved architecture choices.
