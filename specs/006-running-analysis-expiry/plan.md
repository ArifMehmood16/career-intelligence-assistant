# Implementation plan — running analysis expiry

Scope: [spec.md](spec.md), PLAN/BACKLOG 19.3. Existing Python 3.14/FastAPI,
SQLAlchemy/PostgreSQL and TypeScript/React/Vitest; no new dependencies.

## Technical context and existing modules

`SqlAnalysisWorker.startup` alone calls `recover_stale_running`. Reuse that domain
transition in startup and a periodic five-second worker-loop sweep. Use existing
`get_for_update` and `analysis.fail_job` in short-lived units of work to serialize
with publication. `_record_failure` must return terminal/deleted outcomes without
writing over them. `ResiliencePolicy` must check the existing cancellation context
before each physical retry. Existing cancellable wrappers already check after
successful provider responses. `domain.progress.settle` marks a failed job's
running task stopped for the API; the presentational component must respect the
terminal job state and explain batched counters using existing styles.

## Constitution check (before and after design)

Pass: one analysis path; incomplete work publishes no score; pure domain timeout;
existing SQL persistence, provider gate, cancellation/context and bounded threads.
No vendor-name branches, evidence trimming, migrations, new infrastructure or
personal-data/model development calls. All requirements have regression tasks.
No unresolved technical choices. Retain the existing 15-minute total limit.

## Design

- Extract a shared expiry sweep; re-read locked jobs and recover only current
  running rows. Keep safe `stale_running`, with a message describing the running
  time limit rather than claiming the process stopped.
- Call the sweep periodically even when every executor slot is occupied. Handle
  sweep database failures through the existing safe loop-error boundary.
- Preserve terminal failures/success and removed rows in late failure handling.
- Check cancellation at each retry boundary; an already dispatched HTTP call may
  occupy its thread until it returns, but cannot publish or dispatch another call.
- Explain batch counts in running judge/recheck UI without advancing counters.

## Source structure and validation

Backend: adapters/persistence/analysis_worker.py, domain/jobs.py,
adapters/providers/resilience.py; regression tests beside existing SQL worker and
provider resilience tests. Frontend: AnalysisProgress.tsx and its component tests.
Reuse existing gallery props, units and progress settlement. Synthetic SQL tests
hold a provider using events and advance an injected clock rather than waiting
15 minutes. Release all held threads during teardown. Run focused checks then
`make lint`, `make test`, `make test-integration` against a disposable cluster.

## Complexity and limitations

No additional abstraction, schema or settings. The five-second sweep depends on a
healthy worker/database. Cooperative cancellation does not kill synchronous Python
threads or undo a model request already sent. Broader release gates remain open.
