# Implementation Plan: Synthetic analysis benchmark

Branch: `feat/phase-19-synthetic-benchmark` | Date: 2026-10-02
Spec: [spec.md](spec.md) | Root: [PLAN 19.4](../../PLAN.md#194--prove-the-current-product)

## Summary

Build a benchmark driving `RoleAnalysisV2`, `DocumentIndexer`, `RequirementJudge`
and the configured rubric. Use existing hermetic index/search adapters as explicit
benchmark fixtures, with a fresh cache per cold/warm pair. Intercept the existing
HTTP transport to count physical requests, including failures, retries and digest
lookups. Reuse progress/accounting for stage attribution; do not change production
providers or progress behavior. Fix the user-reported migration naming defect first.

## Technical Context

Language: existing Python 3.14. Dependencies: standard library, installed Pydantic,
httpx and provider/application modules. No new package or lock changes.
Storage: ephemeral benchmark fixtures only; no database URL, migration execution or
production persistence fallback. Report written only on explicit output selection.
Testing: existing pytest; new meaningful regression tests authored but not executed.
Platform: local command line. Scope: fixture pairs in the existing manifest.
Performance: report observed application-cache cold/warm timing, not a target SLA.
Constraints: synthetic inputs, explicit live opt-in, existing hosted gate, safe output.

## Constitution Check

Pre-design and post-design review: aligned with all six principles. Application
code remains unchanged, the domain still computes fit, and failed analysis produces
no score. Existing provider builders enforce egress and model execution policies.
A transport decorator counts requests without storing payloads. Fresh fixture caches
are restricted to this measurement command. Live results explicitly identify fixture
retrieval. No release checkbox closes on implementation alone.

Human exceptions recorded: implement 19.4 before earlier deferred checks; write tests
without red/green execution; continue from the current consolidated/adoption branch
rather than obsolete main. The reported naming defect is a 19.1 prerequisite, not a
pipeline redesign. No unresolved architecture decision or research unknown remains.

## Project Structure

Feature artifacts live in `specs/001-synthetic-analysis-benchmark/`.
New source modules live in `backend/src/career_assistant/ops/`:
`benchmark_cases.py`, `benchmark_probe.py`, `benchmark_runtime.py`, `benchmark.py`.
Tests live in `backend/tests/unit/test_analysis_benchmark.py` and
`test_retirement_migration.py`. Existing `Makefile`, evaluation/run documentation,
PLAN/BACKLOG and development log/journal record delivery and pending verification.

## Delivery Phases

1. Repair final-form check-constraint names with Alembic `op.f()` in upgrade and
   downgrade; author SQL-compilation regression tests using actual metadata.
2. Load and fingerprint named synthetic cases; implement a thread-safe measurement
   probe and transport decorator. Never include URL, body, headers or error text.
3. Assemble existing analysis with measured fixture index/cache boundaries and
   existing provider factories for explicitly opted-in live work. Disable fallback.
4. Emit versioned JSON cold/warm observations, attribution and per-case latency
   summaries. Add a Make command that never loads provider environment by default.
5. Update documentation and commit implementation as unverified. Tests/lint/model
   runs/migrations remain pending. Inspect the diff for scope and privacy.

## Complexity Tracking

No constitution violations, new service, dependency, provider path or public API.
