# Implementation Plan: Retirement verification

**Branch**: `test/phase-19-retirement-verification` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)
**Root gate**: [PLAN 19.1](../../PLAN.md#191--retire-the-competing-analysis).

## Summary

Verify the existing retirement implementation with populated migration and publication-consumer regression tests. Reuse the dedicated integration database and hermetic provider boundary. Fix only demonstrated defects; preserve shared citation/draft value types.

## Technical Context

**Language/Version**: Existing Python 3.14 and TypeScript/React.
**Primary Dependencies**: Existing pytest, SQLAlchemy, Alembic, FastAPI TestClient, pgvector and Vitest; no additions.
**Storage**: PostgreSQL 16 production contract and existing Supabase-layout PostgreSQL 17 CI fixture.
**Testing**: Focused pytest integration, unit architecture/selection guards, full make lint/test/test-integration and CI.
**Target Platform**: Existing modular monolith and feature-oriented web app.
**Project Type**: Existing web application; regression verification.
**Performance Goals**: No new latency claim; result projections never invoke analysis or recompute fit.
**Constraints**: Synthetic inputs; distinct DATABASE_URL/TEST_DATABASE_URL; no personal migrations, hosted calls or schema changes unless a test demonstrates a defect.
**Scale/Scope**: Phase 19.1 only; three stories, existing storage and result interfaces.

## Constitution Check

Before research: evidence validation and pure aggregation preserved; one running architecture; existing adapters and dependencies reused; no vendor branches; isolated synthetic storage; hard deletion and attribution tested; commits and gate closure require observed evidence. All six principles pass.
After design: no new entities, service, dependency or public contract. Read-only research confirms populated upgrade coverage is missing. Regression tests exercise existing implementations and retain historical migrations. All gates pass; no exception.

## Project Structure

Feature records in `specs/009-retirement-verification/`: spec, plan, research, data-model, contracts/retirement.md, quickstart and tasks.
Existing code reused: `backend/migrations/versions/c4e8a1d7b902_retire_legacy_analysis.py`, `adapters/persistence/{role_store,v2_analysis_repos,analysis_worker}.py`, `application/{roles/analysis,ask/workspace_tools}.py`, API routes and current frontend analysis hooks/components.
Tests: `backend/tests/integration/test_retirement_preservation.py`, `test_publication_consumers.py`, existing `test_v2_schema.py`, persistence/deletion tests and `unit/test_current_analysis_worker.py`.
Support: reuse `tests/support/v2_http.py` and `v2_seed.py`; add narrowly scoped historical seed helpers if needed.

**Structure Decision**: Extend the existing test layers. Downgrade only the explicitly dedicated integration schema to the historical revision, seed synthetic mixed results, upgrade and restore head in a finally block. Keep tests serial as existing DDL cycle tests require.

## Implementation sequence

1. US1: populated upgrade preservation, invalidation, mixed versions, task/check invariants; commit passing regressions or defect fix with regression.
2. US2: consistent score, gaps, requirements, ranking, preparation, drafts, Ask/MCP and citation reads; invalidated result exclusion; commit.
3. US3: prove retired worker selection impossible, inspect dead frontend/production paths and run populated deletion tests across current and operational tables.
4. Full lint/hermetic/SQL checks, diff/security/design review and factual documentation update. Close only proven 19.1 checkboxes. Push and create a review PR under standing user authorization; do not merge.

Research found a live historical job defect. Add expected behavioral red tests before correcting c4e8a1d7b902 upgrade. This repairs existing retirement behavior without a new selector or architecture. Already-applied migrations cannot identify overwritten legacy jobs safely; record this limit.
