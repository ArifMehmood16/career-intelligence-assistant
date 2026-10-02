# Tasks: Explain incomplete judging

Input: [spec](spec.md), [plan](plan.md). Root: PLAN 19.2; verification under 19.4.

## Setup and foundation

- [x] T001 Inspect current transport/judge paths and read-only job/accounting metadata.
- [x] T002 Specify bounded change and resolve design/privacy constraints in this directory.

## US1 — Identify incomplete judging

Independent criterion: synthetic failures produce distinct safe categories/counts,
without changing completeness or retry behavior.

- [x] T003 [US1] Author regression cases in backend/tests/unit/test_httpx_transport.py and test_requirement_judge.py; do not execute.
- [x] T004 [US1] Log safe failure phase/category in backend/src/career_assistant/adapters/providers/httpx_transport.py.
- [x] T005 [US1] Log failed judge calls, validation rejection counts and incomplete aggregate in backend/src/career_assistant/application/judge/service.py.

## US2 — Allow slow requests

Independent criterion: existing ignored configuration loads 180 seconds/two retries;
defaults remain unchanged. Successful analysis is separate verification.

- [x] T006 [US2] Update only local config/app.env timeout; inspect non-secret effective settings and optional root overlay.
- [x] T007 [US2] Document restart, bounded waiting and diagnosis limits in docs/model-providers.md and docs/running-locally.md.

## Final checkpoint

- [x] T008 Update PLAN.md, BACKLOG.md, AI_DEVELOPMENT_LOG.md and docs/engineering-journal.md; source/diff/privacy review, formatting, bounded local commit.
- [ ] T009 Run focused/full tests, lint/typecheck/security and synthetic end-to-end verification only after human lifts deferral.

Dependencies: T001–T002 before implementation; T003 before T004–T005; T006–T007
follow independently; T008 after implementation. One agent; no parallel team needed.
Transport and judge regression authoring could be independent file work, but remains
sequential here. Incremental delivery: diagnostics first, local mitigation next,
verification last. Task completion for authoring does not mean tests passed.
