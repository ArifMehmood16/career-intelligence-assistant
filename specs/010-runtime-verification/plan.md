# Implementation Plan: Runtime acceptance verification

**Branch**: `test/phase-19-runtime-verification` | **Date**: 2026-10-07
**Spec**: [spec.md](spec.md) | Root: PLAN 19.2–19.3.

## Summary

Reconcile current milestone status against merged code and acceptance evidence.
Reuse the existing provider contracts. Add missing parser lifecycle and actual
thread cancellation/accounting regressions, fixing only demonstrated defects.

## Technical Context

**Language/Version**: Existing Python 3.14; frontend TypeScript/React unchanged.
**Dependencies**: Existing pytest, FastAPI TestClient and standard-library
multiprocessing/threading; no additions.
**Storage**: No persistence or schema change; temporary synthetic test files only.
**Testing**: Focused provider/runtime pytest, existing frontend progress checks,
Ruff/mypy, full make lint/test and final-head CI.
**Target Platform**: Existing local modular monolith on macOS/Linux CI.
**Project Type**: Acceptance verification of an existing web application.
**Performance Goals**: Prove bounded cleanup; no measured model latency claim.
**Constraints**: No personal inputs, provider keys, network model calls or application DB.
**Scope**: Three spec stories; 19.4 evidence gaps remain separate.

## Constitution Check

Before research: all six principles pass. No pipeline, public contract, egress or
storage change. Reuse existing code and prove behavior before ticking gates.
After design: no new dependency or architecture. Test-only spawned helpers receive
immutable synthetic upload data; no sessions/provider objects. Cleanup is bounded
and tests close only pools they created. No exception needed.

## Project Structure

Existing implementations: `backend/src/career_assistant/parsing/process_pool.py`,
`application/providers/{fanout,accounting,cancellable}.py`,
`application/{chunking,indexing,judge}/`, and `main.py` lifespan.
Existing test layers: `backend/tests/unit/test_process_parser.py`,
`test_fanout.py`, provider/judge/indexer contracts and frontend progress tests.
Add a top-level picklable helper in `backend/tests/support/process_parse_probe.py`
for deliberately stalled/crashed children and synthetic PID markers. Exercise
application lifespan in a focused API test without a SQL worker.
Documentation: PLAN/BACKLOG/README, docs/spec-kit and engineering journal, AI log.

No external interface is added or changed, so no new API contract artifact.

## Implementation sequence

1. Inspect all remaining root items and run existing 19.2 contracts (observed pass).
2. Add real spawn timeout/crash/close and lifespan regressions, then actual scoped
   cancellation/progress/retry fanout checks. Existing behavior is already present;
   no artificial red production defect is claimed. Tests must catch removed behavior.
3. Run focused checks and full lint/hermetic suites; inspect complete diff.
4. Close only proven 19.2–19.3 gates, correct stale merged-delivery references,
   split duplicate browser smoke/startup work and separate migration/security proof.
5. Commit/push one task branch and open one review PR under standing authorization.
   Do not merge. Final-head CI remains enforced.
