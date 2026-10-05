# Running analysis expiry and batch progress

Created 2026-10-05. Branch: `fix/phase-19-analysis-timeout`.
Scope: human-reported stalled analysis; [PLAN 19.3](../../PLAN.md#193--bounded-concurrency-and-useful-progress)
and its [BACKLOG item](../../BACKLOG.md#now--verify-one-working-architecture).

## User scenarios and testing

### US1 — Stop an expired analysis visibly (P1)

As a candidate, I need an analysis that exceeds the existing running limit to
stop showing endless progress without restarting the application.

Acceptance: with a synthetic provider held in flight, advancing the worker clock
past the existing 15-minute running limit makes the job failed and its incomplete
role unscored on the next recovery sweep, before the provider returns. A fresh job
and an already completed job remain unchanged. Late responses cannot publish a
score or replace the expiry reason. Removed jobs remain removed.

### US2 — Understand batch progress (P2)

As a candidate, I need to understand why judging can remain at zero while work
is pending, without claiming any unvalidated requirements are complete.

Acceptance: running judge/recheck progress explains that counts update on batch
completion. Failed jobs stop animating and display the existing stopped-task state.
Completed/queued states do not show the running-batch explanation.

## Requirements

- FR-001: Recover expired running jobs during normal operation, reusing the
  existing running timeout and safe `stale_running` code; recover on the next
  five-second sweep plus the worker polling delay while worker/database are available.
- FR-002: Lock and re-read current job state before expiry/failure persistence;
  terminal outcomes and deleted jobs must survive late worker failures.
- FR-003: Existing cancellation checks must discard late successful results and
  prevent subsequent physical provider attempts after expiry.
- FR-004: Show honest batch-completion guidance while judging/rechecking;
  terminal jobs have no active spinner even if their saved task was running.
- FR-005: Use synthetic regressions and an isolated disposable database. Do not
  dispatch paid model requests, change the selected model, or write personal data.

## Success criteria

- SC-001: A blocked synthetic analysis expires before its provider is released;
  the API exposes a failed, unscored analysis and keeps that state after release.
- SC-002: Focused expiry, terminal-state, retry-cancellation and UI regressions
  pass, together with full lint, hermetic and PostgreSQL integration checks.
- SC-003: Current operational docs explain the total running limit, batched
  counters and cooperative cancellation. No broader Phase 19 gate is closed.

## Assumptions and limits

The earlier personal job was still judging after about 20 minutes and became
`stale_running` at restart. The next run completed initial judging in about 96
seconds. Metadata proves missing runtime expiry; it does not prove why the old
provider call failed to return. Keep the existing 15-minute total running limit.
Thread cancellation is cooperative; an already dispatched synchronous HTTP call
is not forcibly interrupted. No schema, API, provider or architecture change.
